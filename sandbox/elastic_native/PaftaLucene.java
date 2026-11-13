/* Native Apache Lucene teaching adapter, original Pafta integration.
 * QueryParser syntax and automata/positions are provided by Apache Lucene.
 * No Elasticsearch server, networking, external index or process is used.
 * Primary docs: https://lucene.apache.org/core/9_12_3/queryparser/
 * ES additions: typed points, indexed-value exists, pure-negative repair.
 */
import java.io.*;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.*;
import java.time.format.DateTimeParseException;
import java.util.*;
import org.apache.lucene.analysis.*;
import org.apache.lucene.analysis.core.KeywordTokenizer;
import org.apache.lucene.analysis.LowerCaseFilter;
import org.apache.lucene.analysis.standard.StandardTokenizer;
import org.apache.lucene.analysis.miscellaneous.PerFieldAnalyzerWrapper;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.document.*;
import org.apache.lucene.index.*;
import org.apache.lucene.queryparser.classic.*;
import org.apache.lucene.search.*;
import org.apache.lucene.store.ByteBuffersDirectory;
import org.apache.lucene.util.BytesRef;
import org.apache.lucene.util.Version;

public final class PaftaLucene {
    static final String EXISTS = "__pafta_exists";
    static final String ROW = "__pafta_row";
    static final String DEFAULT = "__pafta_default_forbidden";

    static final class FieldAnalyzer extends Analyzer {
        final boolean text, lower;
        FieldAnalyzer(boolean text, boolean lower) { this.text = text; this.lower = lower || text; }
        @Override protected TokenStreamComponents createComponents(String field) {
            Tokenizer tokenizer = text ? new StandardTokenizer() : new KeywordTokenizer();
            TokenStream stream = lower ? new LowerCaseFilter(tokenizer) : tokenizer;
            return new TokenStreamComponents(tokenizer, stream);
        }
        @Override protected TokenStream normalize(String field, TokenStream input) {
            return lower ? new LowerCaseFilter(input) : input;
        }
        @Override public int getPositionIncrementGap(String field) { return text ? 100 : 0; }
    }

    static final class Spec {
        final String name, type;
        final boolean lower, indexed;
        final Integer ignoreAbove;
        final Object nullValue;
        Spec(String name, Map<String,Object> raw) {
            if (!name.matches("[A-Za-z@][A-Za-z0-9_.@-]*") || name.startsWith("__pafta"))
                throw bad("Desteklenmeyen/ayrılmış alan adı: " + name);
            this.name = name;
            this.type = str(raw.get("type"), "mapping.type");
            if (!Set.of("keyword","text","long","integer","double","date","boolean").contains(type))
                throw bad("Desteklenmeyen mapping türü: " + type + "; nested/object desteklenmez.");
            for (String key : raw.keySet())
                if (!Set.of("type","analyzer","normalizer","ignore_above","null_value","index").contains(key))
                    throw bad("Desteklenmeyen mapping seçeneği: " + name + "." + key);
            if (raw.containsKey("analyzer") && (!type.equals("text") || !"standard".equals(raw.get("analyzer"))))
                throw bad("Yalnız text analyzer=standard desteklenir.");
            this.lower = "lowercase".equals(raw.get("normalizer"));
            if (raw.containsKey("normalizer") && (!type.equals("keyword") || !lower))
                throw bad("Yalnız keyword normalizer=lowercase desteklenir.");
            if ((raw.containsKey("ignore_above") || raw.containsKey("null_value")) && !type.equals("keyword"))
                throw bad("ignore_above/null_value yalnız keyword alanlarında desteklenir.");
            this.indexed = !Boolean.FALSE.equals(raw.get("index"));
            if (raw.containsKey("index") && !(raw.get("index") instanceof Boolean)) throw bad("index boolean olmalı.");
            this.ignoreAbove = raw.containsKey("ignore_above") ? Math.toIntExact(integral(raw.get("ignore_above"))) : null;
            if (ignoreAbove != null && ignoreAbove < 0) throw bad("ignore_above negatif olamaz.");
            this.nullValue = raw.get("null_value");
            if (nullValue != null && !(nullValue instanceof String)) throw bad("keyword null_value metin olmalı.");
        }
        boolean point() { return Set.of("long","integer","double","date").contains(type); }
    }

    static IllegalArgumentException bad(String message) { return new IllegalArgumentException(message); }
    static String str(Object value, String label) {
        if (!(value instanceof String)) throw bad(label + " metin olmalı.");
        return (String)value;
    }
    @SuppressWarnings("unchecked") static Map<String,Object> map(Object value) {
        if (!(value instanceof Map)) throw bad("JSON nesnesi gerekli.");
        return (Map<String,Object>)value;
    }
    @SuppressWarnings("unchecked") static List<Object> list(Object value) {
        if (!(value instanceof List)) throw bad("JSON listesi gerekli.");
        return (List<Object>)value;
    }
    static long integral(Object value) {
        try {
            if (value instanceof Boolean || value == null) throw new NumberFormatException();
            return new BigDecimal(value.toString()).longValueExact();
        } catch (ArithmeticException | NumberFormatException error) { throw bad("64-bit tamsayı gerekli: " + value); }
    }
    static double decimal(Object value) {
        if (value instanceof Boolean || value == null) throw bad("Sonlu double gerekli.");
        try {
            double number = Double.parseDouble(value.toString());
            if (!Double.isFinite(number)) throw new NumberFormatException();
            return number;
        } catch (NumberFormatException error) { throw bad("Sonlu double gerekli: " + value); }
    }
    static long date(Object value) {
        if (value instanceof Number) return integral(value);
        String text = str(value, "date");
        if (!text.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{1,3})?(Z|[+-][0-9]{2}:[0-9]{2})"))
            throw bad("date metni açık saat dilimli tam ISO timestamp (en fazla 3 kesir hanesi) olmalı; sayısal tarih metni, kısmi tarih/date math desteklenmez.");
        try { return Instant.parse(text).toEpochMilli(); }
        catch (DateTimeParseException ignored) {
            try { return OffsetDateTime.parse(text).toInstant().toEpochMilli(); }
            catch (DateTimeParseException error) {
                throw bad("date açık saat dilimli ISO-8601 timestamp veya epoch_millis olmalı; kısmi tarih/date math desteklenmez: " + text);
            }
        }
    }

    static final class Context implements AutoCloseable {
        final Map<String,Spec> specs = new LinkedHashMap<>();
        final Analyzer analyzer;
        final List<Object> documents;
        Context(Map<String,Object> mapping, List<Object> documents) {
            if (mapping.isEmpty() || mapping.size() > 128) throw bad("Mapping 1..128 alan içermeli.");
            Map<String,Analyzer> analyzers = new HashMap<>();
            for (var entry : mapping.entrySet()) {
                Spec spec = new Spec(entry.getKey(), map(entry.getValue()));
                specs.put(spec.name, spec);
                analyzers.put(spec.name, new FieldAnalyzer(spec.type.equals("text"), spec.lower));
            }
            analyzer = new PerFieldAnalyzerWrapper(new FieldAnalyzer(false, false), analyzers);
            this.documents = documents;
            if (documents.size() > 10000) throw bad("En fazla 10000 belge desteklenir.");
        }
        Spec spec(String field) {
            Spec result = specs.get(field);
            if (result == null) throw bad("Açık, mapping'de tanımlı alan gerekli: " + field + "; default field/alan jokeri/iç alanlar desteklenmez.");
            if (!result.indexed) throw bad("index:false alan sorgulanamaz: " + field);
            return result;
        }
        String normalized(String field, String value) { return analyzer.normalize(field, value).utf8ToString(); }
        Query exists(String field) { spec(field); return new TermQuery(new Term(EXISTS, field)); }
        Query exact(String field, Object value, boolean phrase, boolean allTerms) throws IOException {
            Spec spec = spec(field);
            if (spec.point()) return range(field, value, value, true, true);
            if (spec.type.equals("boolean")) {
                String token = value instanceof Boolean ? value.toString() : str(value, "boolean sorgu");
                if (!token.equals("true") && !token.equals("false")) throw bad("boolean sorgusu true/false olmalı.");
                return new TermQuery(new Term(field, token));
            }
            String text = str(value, "Metin alanı sorgusu");
            if (spec.type.equals("keyword")) return new TermQuery(new Term(field, normalized(field, text)));
            org.apache.lucene.util.QueryBuilder builder = new org.apache.lucene.util.QueryBuilder(analyzer);
            Query result = phrase ? builder.createPhraseQuery(field, text) :
                builder.createBooleanQuery(field, text, allTerms ? BooleanClause.Occur.MUST : BooleanClause.Occur.SHOULD);
            return result == null ? new MatchNoDocsQuery("Analyzer hiç terim üretmedi") : result;
        }
        Query range(String field, Object low, Object high, boolean includeLow, boolean includeHigh) {
            Spec spec = spec(field);
            if (spec.type.equals("boolean")) throw bad("boolean aralıkları desteklenmez.");
            if (spec.type.equals("double")) {
                double lo = low == null ? Double.NEGATIVE_INFINITY : decimal(low);
                double hi = high == null ? Double.POSITIVE_INFINITY : decimal(high);
                if (!includeLow && low != null) lo = DoublePoint.nextUp(lo);
                if (!includeHigh && high != null) hi = DoublePoint.nextDown(hi);
                return Double.compare(lo, hi) > 0 ? new MatchNoDocsQuery() : DoublePoint.newRangeQuery(field, lo, hi);
            }
            if (spec.point()) {
                long lo = low == null ? Long.MIN_VALUE : spec.type.equals("date") ? date(low) : integral(low);
                long hi = high == null ? Long.MAX_VALUE : spec.type.equals("date") ? date(high) : integral(high);
                if ((!includeLow && low != null && lo == Long.MAX_VALUE) || (!includeHigh && high != null && hi == Long.MIN_VALUE)) return new MatchNoDocsQuery();
                if (!includeLow && low != null) lo++;
                if (!includeHigh && high != null) hi--;
                if (spec.type.equals("integer")) { lo = Math.max(lo, Integer.MIN_VALUE); hi = Math.min(hi, Integer.MAX_VALUE); }
                return lo > hi ? new MatchNoDocsQuery() : LongPoint.newRangeQuery(field, lo, hi);
            }
            return new TermRangeQuery(field,
                low == null ? null : new BytesRef(normalized(field, str(low,"Alt sınır"))),
                high == null ? null : new BytesRef(normalized(field, str(high,"Üst sınır"))), includeLow, includeHigh);
        }
        void add(Document document, Spec spec, Object raw) {
            if (!spec.indexed) return;
            Object value = raw == null ? spec.nullValue : raw;
            if (value == null) return;
            if (value instanceof Map || value instanceof List) throw bad("Flat skaler değer gerekli: " + spec.name);
            switch (spec.type) {
                case "keyword": {
                    String text = str(value, spec.name);
                    if (spec.ignoreAbove != null && text.length() > spec.ignoreAbove) return;
                    document.add(new StringField(spec.name, normalized(spec.name, text), Field.Store.NO));
                    break;
                }
                case "text": document.add(new TextField(spec.name, str(value,spec.name), Field.Store.NO)); break;
                case "boolean":
                    if (!(value instanceof Boolean)) throw bad("boolean belge alanı true/false olmalı: " + spec.name);
                    document.add(new StringField(spec.name,value.toString(),Field.Store.NO)); break;
                case "double":
                    if (!(value instanceof Number)) throw bad("double belge alanı JSON sayı olmalı.");
                    document.add(new DoublePoint(spec.name,decimal(value))); break;
                case "date": document.add(new LongPoint(spec.name,date(value))); break;
                default:
                    if (!(value instanceof Number)) throw bad("Tamsayı belge alanı JSON sayı olmalı.");
                    long number = integral(value);
                    if (spec.type.equals("integer") && (number < Integer.MIN_VALUE || number > Integer.MAX_VALUE)) throw bad("integer aralığı aşıldı.");
                    document.add(new LongPoint(spec.name,number));
            }
            document.add(new StringField(EXISTS,spec.name,Field.Store.NO));
        }
        List<Integer> search(Query query) throws Exception {
            try (var directory = new ByteBuffersDirectory()) {
                try (var writer = new IndexWriter(directory,new IndexWriterConfig(analyzer))) {
                    for (int row = 0; row < documents.size(); row++) {
                        Map<String,Object> raw = map(documents.get(row));
                        // Unmapped _source keys (including display id) are kept
                        // out of the native index, never implicitly queryable.
                        Document document = new Document();
                        document.add(new StringField(ROW,Integer.toString(row),Field.Store.YES));
                        for (Spec spec : specs.values()) if (raw.containsKey(spec.name)) {
                            Object value = raw.get(spec.name);
                            if (value instanceof List) for (Object item : list(value)) add(document,spec,item);
                            else add(document,spec,value);
                        }
                        writer.addDocument(document);
                    }
                    writer.commit();
                }
                try (var reader = DirectoryReader.open(directory)) {
                    IndexSearcher searcher = new IndexSearcher(reader);
                    List<Integer> result = new ArrayList<>();
                    for (ScoreDoc hit : searcher.search(query,Math.max(1,documents.size()),Sort.INDEXORDER).scoreDocs)
                        result.add(Integer.parseInt(reader.storedFields().document(hit.doc).get(ROW)));
                    Collections.sort(result);
                    return result;
                }
            }
        }
        Query ast(Map<String,Object> node) throws Exception {
            String op = str(node.get("op"),"AST.op");
            if (op.equals("and") || op.equals("or")) {
                List<Object> args = list(node.get("args"));
                if (args.isEmpty()) return op.equals("and") ? new MatchAllDocsQuery() : new MatchNoDocsQuery();
                BooleanQuery.Builder builder = new BooleanQuery.Builder();
                for (Object child : args) builder.add(ast(map(child)),op.equals("and") ? BooleanClause.Occur.MUST : BooleanClause.Occur.SHOULD);
                if (op.equals("or")) builder.setMinimumNumberShouldMatch(1);
                return builder.build();
            }
            if (op.equals("not")) return new BooleanQuery.Builder().add(new MatchAllDocsQuery(),BooleanClause.Occur.FILTER)
                .add(ast(map(node.get("arg"))),BooleanClause.Occur.MUST_NOT).build();
            if (op.equals("ids")) {
                List<BytesRef> ids = new ArrayList<>();
                for (Object id : list(node.get("indices"))) {
                    long value = integral(id);
                    if (value < 0 || value >= documents.size()) throw bad("AST ids belge indeksi aralık dışında.");
                    ids.add(new BytesRef(Long.toString(value)));
                }
                return new TermInSetQuery(ROW,ids);
            }
            String field = str(node.get("field"),"AST.field");
            if (op.equals("exists")) return exists(field);
            if (op.equals("match")) return exact(field,node.get("value"),Boolean.TRUE.equals(node.get("phrase")),false);
            if (op.equals("range")) {
                String cmp = str(node.get("cmp"),"AST.cmp"); Object value = node.get("value");
                if (value == null) throw bad("Aralık değeri null olamaz.");
                return switch(cmp) {
                    case ">", "gt" -> range(field,value,null,false,true);
                    case ">=", "gte" -> range(field,value,null,true,true);
                    case "<", "lt" -> range(field,null,value,true,false);
                    case "<=", "lte" -> range(field,null,value,true,true);
                    default -> throw bad("Desteklenmeyen AST karşılaştırması: " + cmp);
                };
            }
            if (op.equals("wildcard")) {
                Spec spec = spec(field);
                if (!Set.of("keyword","text").contains(spec.type)) throw bad("Joker yalnız keyword/text alanında kullanılabilir.");
                return new WildcardQuery(new Term(field,normalized(field,str(node.get("pattern"),"wildcard.pattern"))));
            }
            throw bad("Desteklenmeyen AST op: " + op);
        }
        @Override public void close() { analyzer.close(); }
    }

    static final class Parser extends QueryParser {
        final Context context;
        Parser(Context context) {
            super(PaftaLucene.DEFAULT,context.analyzer); this.context = context;
            setDefaultOperator(Operator.OR); setAllowLeadingWildcard(true); setDeterminizeWorkLimit(10000);
        }
        @Override protected Query getFieldQuery(String field, String text, boolean quoted) throws ParseException {
            try {
                if (field.equals("_exists_")) return context.exists(text);
                Spec spec = context.spec(field);
                if (spec.point() || spec.type.equals("boolean") || spec.type.equals("keyword")) {
                    if (spec.point() && !quoted) for (String cmp : List.of(">=","<=",">","<")) if (text.startsWith(cmp)) {
                        String value = text.substring(cmp.length());
                        return context.range(field,cmp.startsWith(">")?value:null,cmp.startsWith("<")?value:null,
                                             !cmp.equals(">"),!cmp.equals("<"));
                    }
                    return context.exact(field,text,false,false);
                }
                return super.getFieldQuery(field,text,quoted);
            } catch (IOException error) { throw new ParseException(error.getMessage()); }
        }
        @Override protected Query getRangeQuery(String field,String low,String high,boolean incLow,boolean incHigh) {
            return context.range(field,low,high,incLow,incHigh);
        }
        @Override protected Query getWildcardQuery(String field,String text) throws ParseException {
            if (field.equals("*") && text.equals("*")) return new MatchAllDocsQuery();
            context.spec(field);
            if (text.equals("*")) return context.exists(field);
            textual(field); return super.getWildcardQuery(field,text);
        }
        void textual(String field) {
            if (!Set.of("text","keyword").contains(context.spec(field).type)) throw bad("Fuzzy/regex/joker yalnız text/keyword alanlarında desteklenir.");
        }
        @Override protected Query getPrefixQuery(String field,String text) throws ParseException { textual(field); return super.getPrefixQuery(field,text); }
        @Override protected Query getRegexpQuery(String field,String text) throws ParseException { textual(field); return super.getRegexpQuery(field,text); }
        @Override protected Query getFuzzyQuery(String field,String text,float similarity) throws ParseException { textual(field); return super.getFuzzyQuery(field,text,similarity); }
        @Override protected Query getBooleanQuery(List<BooleanClause> clauses) throws ParseException {
            Query result = super.getBooleanQuery(clauses);
            if (result instanceof BooleanQuery && !clauses.isEmpty() && clauses.stream().allMatch(c -> c.getOccur()==BooleanClause.Occur.MUST_NOT)) {
                BooleanQuery.Builder builder = new BooleanQuery.Builder();
                builder.add(new MatchAllDocsQuery(),BooleanClause.Occur.FILTER);
                for (BooleanClause clause : clauses) builder.add(clause);
                return builder.build();
            }
            return result;
        }
    }

    static void rejectBoosts(String query) {
        boolean quoted=false, regex=false, escaped=false;
        for (int i=0;i<query.length();i++) {
            char ch=query.charAt(i);
            if (escaped) { escaped=false; continue; }
            if (ch=='\\') { escaped=true; continue; }
            if (ch=='"' && !regex) quoted=!quoted;
            else if (ch=='/' && !quoted) regex=!regex;
            else if (ch=='^' && !quoted && !regex) throw bad("Boost/scoring seçenekleri bu üyelik tezgâhında desteklenmez.");
        }
    }

    static List<String> analyze(String text,String analyzer,boolean lower) throws IOException {
        if (!Set.of("standard","keyword").contains(analyzer)) throw bad("Analyzer standard/keyword olmalı.");
        try (Analyzer a = new FieldAnalyzer(analyzer.equals("standard"),lower); TokenStream stream=a.tokenStream("value",text)) {
            CharTermAttribute term=stream.addAttribute(CharTermAttribute.class); List<String> result=new ArrayList<>();
            stream.reset(); while(stream.incrementToken()) result.add(term.toString()); stream.end(); return result;
        }
    }

    public static void main(String[] args) {
        System.setOut(new PrintStream(System.out, true, StandardCharsets.UTF_8));
        System.setErr(new PrintStream(System.err, true, StandardCharsets.UTF_8));
        try {
            String input=new String(System.in.readAllBytes(),StandardCharsets.UTF_8);
            Map<String,Object> job=map(new Json(input).parse());
            String mode=str(job.get("mode"),"mode"); Object output;
            if (mode.equals("version")) output=Map.of("version","Apache Lucene "+Version.LATEST);
            else if (mode.equals("analyze")) output=Map.of("tokens",analyze(str(job.get("text"),"text"),str(job.get("analyzer"),"analyzer"),Boolean.TRUE.equals(job.get("lowercase"))));
            else try(Context context=new Context(map(job.get("mapping")),list(job.get("documents")))) {
                Query query;
                if (mode.equals("ast")) query=context.ast(map(job.get("ast")));
                else if (mode.equals("query")) {
                    String text=str(job.get("query"),"query"); rejectBoosts(text);
                    query=new Parser(context).parse(text);
                } else throw bad("Bilinmeyen mode: "+mode);
                output=Map.of("indices",context.search(query));
            }
            System.out.println(Json.write(output));
        } catch (Exception | LinkageError error) {
            System.out.println(Json.write(Map.of("error",error.getClass().getSimpleName()+": "+String.valueOf(error.getMessage()))));
            System.exit(2);
        }
    }

    /** JSON transport only; query parsing is exclusively Lucene's JavaCC parser. */
    static final class Json {
        final String text; int at=0,depth=0;
        Json(String text) { this.text=text; }
        void ws() { while(at<text.length() && Character.isWhitespace(text.charAt(at))) at++; }
        Object parse() { Object result=value(); ws(); if(at!=text.length()) throw bad("JSON sonunda fazla veri."); return result; }
        Object value() {
            ws(); if(++depth>128) throw bad("JSON çok derin.");
            try {
                if(at>=text.length()) throw bad("JSON değeri eksik."); char ch=text.charAt(at);
                if(ch=='"') return string();
                if(ch=='{') {
                    at++; Map<String,Object> object=new LinkedHashMap<>(); ws();
                    if(take('}')) return object;
                    do { ws(); String key=string(); ws(); require(':'); if(object.containsKey(key)) throw bad("JSON yinelenen alan: "+key); object.put(key,value()); ws(); } while(take(','));
                    require('}'); return object;
                }
                if(ch=='[') {
                    at++; List<Object> array=new ArrayList<>(); ws(); if(take(']')) return array;
                    do { array.add(value()); ws(); } while(take(',')); require(']'); return array;
                }
                if(text.startsWith("true",at)) { at+=4; return true; }
                if(text.startsWith("false",at)) { at+=5; return false; }
                if(text.startsWith("null",at)) { at+=4; return null; }
                int start=at;
                if(ch=='-') at++;
                while(at<text.length() && Character.isDigit(text.charAt(at))) at++;
                if(at<text.length() && text.charAt(at)=='.') { at++; while(at<text.length() && Character.isDigit(text.charAt(at))) at++; }
                if(at<text.length() && (text.charAt(at)=='e'||text.charAt(at)=='E')) {
                    at++; if(at<text.length() && (text.charAt(at)=='+'||text.charAt(at)=='-')) at++;
                    while(at<text.length() && Character.isDigit(text.charAt(at))) at++;
                }
                if(at==start) throw bad("JSON değeri geçersiz.");
                String numberText = text.substring(start,at);
                BigDecimal number = new BigDecimal(numberText);
                // BigDecimal has no signed zero; retain the IEEE-754 sign of
                // JSON floating zero without sacrificing integral precision.
                if (number.signum() == 0 && numberText.startsWith("-") &&
                    (numberText.contains(".") || numberText.contains("e") || numberText.contains("E")))
                    return Double.valueOf(-0.0d);
                return number;
            } finally { depth--; }
        }
        boolean take(char ch) { if(at<text.length() && text.charAt(at)==ch) { at++; return true; } return false; }
        void require(char ch) { if(!take(ch)) throw bad("JSON beklenen karakter: "+ch); }
        String string() {
            require('"'); StringBuilder value=new StringBuilder();
            while(at<text.length()) {
                char ch=text.charAt(at++); if(ch=='"') return value.toString();
                if(ch=='\\') {
                    if(at>=text.length()) throw bad("JSON kaçış eksik."); ch=text.charAt(at++);
                    switch(ch) {
                        case '"','\\','/' -> value.append(ch);
                        case 'b' -> value.append('\b'); case 'f' -> value.append('\f'); case 'n' -> value.append('\n');
                        case 'r' -> value.append('\r'); case 't' -> value.append('\t');
                        case 'u' -> { if(at+4>text.length()) throw bad("JSON Unicode kaçış eksik."); value.append((char)Integer.parseInt(text.substring(at,at+4),16)); at+=4; }
                        default -> throw bad("JSON kaçışı geçersiz.");
                    }
                } else { if(ch<32) throw bad("JSON kontrol karakteri."); value.append(ch); }
            }
            throw bad("JSON metni kapanmamış.");
        }
        static String write(Object value) {
            if(value==null) return "null";
            if(value instanceof String) {
                StringBuilder out=new StringBuilder("\"");
                for(char ch:((String)value).toCharArray()) switch(ch) {
                    case '"' -> out.append("\\\""); case '\\' -> out.append("\\\\");
                    case '\n' -> out.append("\\n"); case '\r' -> out.append("\\r"); case '\t' -> out.append("\\t");
                    default -> { if(ch<32) out.append(String.format("\\u%04x",(int)ch)); else out.append(ch); }
                }
                return out.append('"').toString();
            }
            if(value instanceof Map) { List<String> pairs=new ArrayList<>(); ((Map<?,?>)value).forEach((k,v)->pairs.add(write(k.toString())+":"+write(v))); return "{"+String.join(",",pairs)+"}"; }
            if(value instanceof List) { List<String> values=new ArrayList<>(); for(Object item:(List<?>)value) values.add(write(item)); return "["+String.join(",",values)+"]"; }
            return value.toString();
        }
    }
}
