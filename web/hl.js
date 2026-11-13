// Python sözdizimi renklendirici: metni [sınıf, parça] listesine böler.
const KW = new Set(("False None True and as assert async await break class continue def del elif else except " +
  "finally for from global if import in is lambda nonlocal not or pass raise return try while with yield").split(" "));
const SOFT = new Set(["match", "case", "type"]);
const CONST = new Set(["True", "False", "None"]);
const BI = new Set(("abs all any ascii bin bool breakpoint bytearray bytes callable chr classmethod compile complex " +
  "delattr dict dir divmod enumerate eval exec filter float format frozenset getattr globals hasattr hash help hex " +
  "id input int isinstance issubclass iter len list locals map max memoryview min next object oct open ord pow print " +
  "property range repr reversed round set setattr slice sorted staticmethod str sum super tuple type vars zip " +
  "__import__ NotImplemented Ellipsis Exception BaseException ValueError TypeError KeyError IndexError NameError " +
  "ZeroDivisionError AttributeError RuntimeError StopIteration OSError FileNotFoundError ImportError " +
  "NotImplementedError AssertionError PermissionError TimeoutError ConnectionError UnicodeDecodeError").split(" "));

const RE = /(#[^\n]*)|((?:[rRbBuUfF]{1,2})?(?:"""[\s\S]*?(?:"""|$)|'''[\s\S]*?(?:'''|$)|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?))|(\b0[xX][\da-fA-F_]+\b|\b0[bB][01_]+\b|\b0[oO][0-7_]+\b|(?:\b\d[\d_]*\.?[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d+)?j?)|(@[A-Za-z_][\w.]*)|([A-Za-z_À-￿][\wÀ-￿]*)|(\s+)|([^\s\w])/gy;

// match/case yalnızca satırın ilk kelimesiyse ve satır ':' ile bitiyorsa anahtar kelimedir.
function isSoftKw(src, at) {
  const start = src.lastIndexOf("\n", at - 1) + 1;
  let end = src.indexOf("\n", at);
  if (end < 0) end = src.length;
  const line = src.slice(start, end);
  return src.slice(start, at).trim() === "" && /^\s*(match|case|type)\s+[^=\s]/.test(line) &&
    (/:\s*(#.*)?$/.test(line) || /^\s*type\s+\w+\s*=/.test(line));
}

export function tokenize(src) {
  const out = [];
  let m, prevWord = "";
  RE.lastIndex = 0;
  while (RE.lastIndex < src.length && (m = RE.exec(src))) {
    const [t, com, str, num, dec, word, ws] = m;
    let cls = "";
    if (com !== undefined) cls = "com";
    else if (str !== undefined) cls = "str";
    else if (num !== undefined) cls = "num";
    else if (dec !== undefined) cls = "dec";
    else if (word !== undefined) {
      if (CONST.has(word)) cls = "const";
      else if (KW.has(word)) cls = "kw";
      else if (SOFT.has(word) && isSoftKw(src, m.index)) cls = "kw";
      else if (prevWord === "def" || prevWord === "class") cls = "fn";
      else if (word === "self" || word === "cls") cls = "self";
      else if (BI.has(word)) cls = "bi";
      prevWord = word;
    } else if (ws === undefined) {
      cls = "op";
      prevWord = "";
    }
    if (out.length && out[out.length - 1][0] === cls) out[out.length - 1][1] += t;
    else out.push([cls, t]);
  }
  if (RE.lastIndex < src.length) out.push(["", src.slice(RE.lastIndex)]);
  return out;
}

export function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ── genel düzenli ifade tabanlı jetonlayıcı ──────────────────────────────────
function kural(re, siniflar) {
  return src => {
    const out = [];
    let m;
    re.lastIndex = 0;
    while (re.lastIndex < src.length && (m = re.exec(src))) {
      let cls = "";
      for (let i = 1; i < m.length; i++) if (m[i] !== undefined) { cls = siniflar[i - 1](m[i], src, m.index); break; }
      if (out.length && out[out.length - 1][0] === cls) out[out.length - 1][1] += m[0];
      else out.push([cls, m[0]]);
      if (m[0] === "") re.lastIndex++;
    }
    if (re.lastIndex < src.length) out.push(["", src.slice(re.lastIndex)]);
    return out;
  };
}

const BASH_KW = new Set("if then else elif fi for in do done while until case esac function return local export readonly select break continue".split(" "));
const BASH_BI = new Set(("echo printf read cd pwd test exit set unset shift source alias declare true false " +
  "grep egrep sed awk cut sort uniq wc head tail tr cat ls find xargs tee date basename dirname mkdir rm cp mv touch chmod seq expr").split(" "));
const tokBash = kural(
  /(#[^\n]*)|('[^']*'?|"(?:\\.|[^"\\])*"?)|(\$\{[^}\n]*\}?|\$\(|\$[A-Za-z_]\w*|\$[0-9#?@*$!-])|(\b\d+\b)|([A-Za-z_][\w-]*)|(\s+)|([^\s\w])/gy,
  [() => "com", () => "str", () => "self", () => "num",
   w => (BASH_KW.has(w) ? "kw" : BASH_BI.has(w) ? "bi" : ""), () => "", () => "op"]);

const PS_KW = new Set(("if elseif else foreach for while do until switch function param return break continue " +
  "try catch finally throw begin process end in filter").split(" "));
const tokPs = kural(
  /(<#[\s\S]*?(?:#>|$)|#[^\n]*)|(@"[\s\S]*?(?:"@|$)|@'[\s\S]*?(?:'@|$)|"(?:`.|[^"`])*"?|'[^']*'?)|(\$(?:env:)?[A-Za-z_]\w*|\$\{[^}\n]*\}?|\$_|\$\(|\$\$)|(-(?:eq|ne|gt|ge|lt|le|like|notlike|match|notmatch|contains|notcontains|in|notin|not|and|or|xor|replace|split|join|is|isnot|as|f)\b)|(\[[A-Za-z_][\w.\[\]]*\])|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][\w]*(?:-[A-Za-z]\w*)?)|(\s+)|([^\s\w])/giy,
  [() => "com", () => "str", () => "self", () => "kw", () => "bi", () => "num",
   w => (PS_KW.has(w.toLowerCase()) ? "kw" : /^[A-Za-z]+-[A-Za-z]+$/.test(w) ? "fn" : ""), () => "", () => "op"]);

const tokRegex = kural(
  /(\(\?(?:P?<[A-Za-z_]\w*>|[:=!]|<[=!]|[aiLmsux]+\)?)|[()])|(\\[dDwWsSbBAZnrtfv]|\\\d+|\\.)|(\[(?:\\.|[^\]\\])*\]?)|([*+?](?:\?)?|\{\d+(?:,\d*)?\}\??)|([\^$])|(\|)|(\.)|([^()\\[*+?{^$|.]+|.)/gy,
  [() => "fn", () => "kw", () => "str", () => "num", () => "dec", () => "op", () => "bi", () => ""]);

const SQL_KW = new Set(("select from where and or not in is like glob between exists as on join inner left right full outer " +
  "cross natural using group by having order asc desc limit offset distinct union all intersect except case when then " +
  "else end insert into values update set delete create table index view drop alter add column rename primary key " +
  "foreign references unique check default constraint begin commit rollback transaction savepoint release with recursive " +
  "over partition window rows range groups preceding following current row unbounded filter nulls first last collate " +
  "escape cast if temp temporary autoincrement returning conflict do nothing explain query plan pragma").split(" "));
const SQL_SABIT = new Set(["null", "true", "false", "current_date", "current_time", "current_timestamp"]);
const SQL_FN = new Set(("count sum avg min max total group_concat string_agg coalesce ifnull nullif iif length lower upper " +
  "substr substring trim ltrim rtrim replace instr round abs sign date time datetime julianday strftime unixepoch printf " +
  "format typeof row_number rank dense_rank ntile lag lead first_value last_value nth_value percent_rank cume_dist " +
  "random hex quote char unicode likely").split(" "));
const tokSql = kural(
  /(--[^\n]*|\/\*[\s\S]*?(?:\*\/|$))|('(?:''|[^'])*'?)|("(?:""|[^"])*"?|`[^`]*`?)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_À-￿][\wÀ-￿]*)|(\s+)|([^\s\w])/gy,
  [() => "com", () => "str", () => "self", () => "num",
   (w, src, at) => {
     const k = w.toLowerCase();
     if (SQL_SABIT.has(k)) return "const";
     if (SQL_FN.has(k) && /^\s*\(/.test(src.slice(at + w.length))) return "bi";
     return SQL_KW.has(k) ? "kw" : "";
   }, () => "", () => "op"]);

const KQL_ISLEC = new Set(("where project project-away project-rename extend summarize sort order by take limit top count " +
  "distinct join kind on print asc desc").split(" "));
const KQL_KW = new Set(("and or not in in~ between contains contains_cs has has_cs startswith startswith_cs endswith " +
  "endswith_cs matches regex inner innerunique leftouter rightouter fullouter leftanti leftsemi").split(" "));
const tokKql = kural(
  /(\/\/[^\n]*)|(@"[^"\n]*"?|@'[^'\n]*'?|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(\$left|\$right)|(\b\d+(?:\.\d+)?(?:ms|d|h|m|s)?\b)|([A-Za-z_À-￿][\wÀ-￿]*(?:-(?:away|rename))?)|(\s+)|([^\s\w])/gy,
  [() => "com", () => "str", () => "self", () => "num",
   (w, src, at) => {
     if (w === "true" || w === "false" || w === "null") return "const";
     if (/^\s*\(/.test(src.slice(at + w.length))) return "bi";
     return KQL_ISLEC.has(w) ? "kw" : KQL_KW.has(w) ? "dec" : "";
   }, () => "", () => "op"]);

const SPL_KOMUT = new Set("search where eval stats table fields rename sort head tail dedup top rare bin bucket rex join".split(" "));
const SPL_KW = new Set(["AND", "OR", "NOT", "by", "BY", "as", "AS", "span", "field", "type", "limit"]);
const tokSpl = kural(
  /("(?:\\.|[^"\\])*"?)|('[^'\n]*'?)|(\b(?:sourcetype|index)(?==))|(\b\d+(?:\.\d+)?[dhm]?\b)|([A-Za-z_À-￿][\wÀ-￿]*\*?)|(\s+)|([^\s\w])/gy,
  [() => "str", () => "self", () => "dec", () => "num",
   (w, src, at) => {
     if (/^\s*\(/.test(src.slice(at + w.length))) return "bi";
     if (SPL_KOMUT.has(w) && /\|\s*$/.test(src.slice(0, at))) return "kw";
     return SPL_KW.has(w) ? "kw" : "";
   }, () => "", () => "op"]);

const JS_KW = new Set(("const let var function return if else for while do switch case break continue new class extends " +
  "super this typeof instanceof in of async await try catch finally throw import export from default yield delete void").split(" "));
const JS_SABIT = new Set(["null", "undefined", "true", "false", "NaN", "Infinity"]);
const JS_BI = new Set(("console Math JSON Object Array String Number Boolean Promise Date Map Set setTimeout setInterval " +
  "parseInt parseFloat document window fetch require module process").split(" "));
const tokJs = kural(
  /(\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$))|(`(?:\\.|[^`\\])*`?|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_$][\w$]*)|(\s+)|([^\s\w])/gy,
  [() => "com", () => "str", () => "num",
   w => (JS_SABIT.has(w) ? "const" : JS_KW.has(w) ? "kw" : JS_BI.has(w) ? "bi" : w === "this" ? "self" : ""),
   () => "", () => "op"]);

const C_KW = new Set(("int char float double void long short unsigned signed struct union enum typedef const static extern " +
  "return if else for while do switch case default break continue sizeof goto size_t").split(" "));
const C_BI = new Set(("printf scanf puts putchar malloc calloc realloc free strlen strcpy strncpy strcmp strncmp strcat " +
  "memcpy memset snprintf sprintf fopen fclose fgets fprintf atoi exit").split(" "));
const tokC = kural(
  /(\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$))|(^[ \t]*#[^\n]*)|("(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(\b0[xX][\da-fA-F]+\b|\b\d+(?:\.\d+)?[uUlLfF]*\b)|([A-Za-z_]\w*)|(\s+)|([^\s\w])/gmy,
  [() => "com", () => "dec", () => "str", () => "num",
   w => (w === "NULL" ? "const" : C_KW.has(w) ? "kw" : C_BI.has(w) ? "bi" : ""), () => "", () => "op"]);

const PHP_KW = new Set(("function return if else elseif foreach as for while do switch case break continue echo print " +
  "array isset empty unset class new public private protected static fn match use namespace require include try catch throw").split(" "));
const PHP_BI = new Set(("strlen count explode implode str_replace strtolower strtoupper trim substr strpos in_array array_keys " +
  "array_map array_filter array_sum json_encode json_decode htmlspecialchars intval sprintf printf var_dump isset").split(" "));
const tokPhp = kural(
  /(\/\/[^\n]*|#[^\n]*|\/\*[\s\S]*?(?:\*\/|$))|(<\?php|\?>)|("(?:\\.|[^"\\])*"?|'(?:\\.|[^'\\])*'?)|(\$[A-Za-z_]\w*)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)|(\s+)|([^\s\w])/gy,
  [() => "com", () => "dec", () => "str", () => "self", () => "num",
   w => (["null", "true", "false", "NULL"].includes(w) ? "const" : PHP_KW.has(w.toLowerCase()) ? "kw" : PHP_BI.has(w) ? "bi" : ""),
   () => "", () => "op"]);

const JAVA_KW = new Set(("abstract boolean break byte case catch char class continue default do double else enum extends final " +
  "finally float for if implements import instanceof int interface long new package private protected public return short static " +
  "super switch synchronized throw throws transient try var void volatile while record sealed permits yield").split(" "));
const JAVA_BI = new Set(("System String Integer Long Double Boolean Character Math Object List ArrayList Map HashMap LinkedHashMap " +
  "TreeMap Set HashSet Optional Arrays Collections Objects StringBuilder Stream Collectors LocalDate Instant Duration " +
  "Exception RuntimeException IllegalArgumentException IllegalStateException NullPointerException").split(" "));
const tokJava = kural(
  /(\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$))|(@[A-Za-z_]\w*)|("""[\s\S]*?(?:"""|$)|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(\b0[xX][\da-fA-F_]+[lL]?\b|\b\d[\d_]*(?:\.\d+)?[lLfFdD]?\b)|([A-Za-z_$][\w$]*)|(\s+)|([^\s\w])/gy,
  [() => "com", () => "dec", () => "str", () => "num",
   w => (["null", "true", "false"].includes(w) ? "const" : w === "this" ? "self" : JAVA_KW.has(w) ? "kw" : JAVA_BI.has(w) ? "bi" : ""),
   () => "", () => "op"]);

const CSHARP_KW = new Set(("abstract as async await base bool break byte case catch char checked class const continue decimal default " +
  "delegate do double else enum event explicit extern finally fixed float for foreach from get global goto group if implicit in " +
  "init int interface internal into is join let lock long namespace new notnull object on operator orderby out override params " +
  "partial private protected public readonly record ref required return sbyte sealed select set short sizeof stackalloc static " +
  "string struct switch throw try typeof uint ulong unchecked unsafe ushort using value var virtual void volatile when where " +
  "while with yield").split(" "));
const CSHARP_BI = new Set(("Console String Int32 Int64 Double Decimal Boolean Char Math Object List Dictionary HashSet IEnumerable " +
  "IQueryable Task ValueTask Action Func Nullable TimeSpan DateTime DateTimeOffset Guid Path File Directory JsonSerializer " +
  "JsonSerializerOptions StringComparison StringComparer StringSplitOptions FormattableString Exception InvalidOperationException " +
  "ArgumentException ArgumentNullException ArgumentOutOfRangeException FormatException KeyNotFoundException OverflowException " +
  "DivideByZeroException ControllerBase IActionResult DbContext DbSet").split(" "));
const tokCsharp = kural(
  /(\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$))|("""[\s\S]*?(?:"""|$)|\$@"(?:""|[^"])*"?|@\$"(?:""|[^"])*"?|@"(?:""|[^"])*"?|\$"(?:\\.|[^"\\\n])*"?|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(\b0[xX][\da-fA-F_]+[uUlL]*\b|\b\d[\d_]*(?:\.\d+)?[mMdDfFlLuU]*\b)|([A-Za-z_]\w*)|(\s+)|([^\s\w])/gy,
  [() => "com", () => "str", () => "num",
   w => (["null", "true", "false"].includes(w) ? "const" : ["this", "base"].includes(w) ? "self" : CSHARP_KW.has(w) ? "kw" : CSHARP_BI.has(w) ? "bi" : ""),
   () => "", () => "op"]);

const SIGMA_KEYS = new Set("title id name status description author date modified references tags logsource category product service detection condition fields falsepositives level".split(" "));
const tokSigma = kural(
  /(#[^\n]*)|('(?:''|[^'])*'?|"(?:\\.|[^"\\])*"?)|(\b(?:true|false|null)\b)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][\w.|*-]*)|(\s+)|([^\s\w])/gy,
  [() => "com", () => "str", () => "const", () => "num",
   w => SIGMA_KEYS.has(w) ? "kw" : /\|/.test(w) ? "fn" : "", () => "", () => "op"]);
const YARA_KEYS = new Set("rule private global meta strings condition import include and or not of them any all none for in at ascii wide nocase fullword xor base64 base64wide true false filesize entrypoint defined with".split(" "));
const tokYara = kural(
  /(\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$))|("(?:\\.|[^"\\])*"?)|(\/(?:\\.|[^\/\\\n])*\/[is]*)|([$#@!][A-Za-z_]\w*|\$)|(\b0[xX][\da-fA-F]+\b|\b\d+(?:KB|MB)?\b)|([A-Za-z_]\w*)|(\s+)|([^\s\w])/gy,
  [() => "com", () => "str", () => "str", () => "self", () => "num",
   w => YARA_KEYS.has(w) ? "kw" : /^(?:uint|int)\d+(?:be)?$/.test(w) ? "bi" : "", () => "", () => "op"]);

// These are display lexers only: no Elastic query is evaluated in the browser.
const ELASTIC_WORDS = new Set("FROM WHERE EVAL STATS COUNT SUM COALESCE SORT ASC DESC NULLS FIRST LAST KEEP BY and or not AND OR NOT TO where sequence by with maxspan until any true false null in like regex head tail sample join runs of missing".split(" "));
const tokElastic = kural(
  /(\/\/[^\n]*)|("(?:\\.|[^"\\])*"?|`(?:``|[^`])*`?)|(\/(?:\\.|[^\/\\\n])*\/)|(\b\d+(?:\.\d+)?(?:ms|s|m|h|d)?\b)|([?@]?[A-Za-z_][\w.~-]*)|(\s+)|([^\s\w])/gy,
  [() => "com", () => "str", () => "str", () => "num",
   w => ELASTIC_WORDS.has(w) ? "kw" : w.includes(".") ? "self" : "", () => "", () => "op"]);
const CMD_WORDS = new Set("echo rem set setlocal endlocal if else not defined exist errorlevel equ neq lss leq gtr geq for in do goto call exit shift cd chdir pushd popd type find findstr sort copy move ren rename md mkdir dir where enabledelayedexpansion disabledelayedexpansion enableextensions".split(" "));
const tokCmd = kural(
  /(^[ \t]*@?rem\b[^\n]*|^[ \t]*::[^\n]*)|("[^"\n]*"?)|(%[^%\n]+%|![^!\n]+!|%%~?[A-Za-z]*[A-Za-z]|%~?[A-Za-z]*[0-9*])|(\b\d+\b)|([A-Za-z_][\w.-]*)|(\s+)|([^\s\w])/gmiy,
  [() => "com", () => "str", () => "self", () => "num",
   w => CMD_WORDS.has(w.toLowerCase()) ? "kw" : "", () => "", () => "op"]);
const PACKET_WORDS = new Set("and or not in contains matches tcp udp sctp ip ip6 ipv6 arp icmp icmp6 host net port portrange src dst ether proto vlan len less greater broadcast multicast tcpflags tcp-syn tcp-ack tcp-fin tcp-rst".split(" "));
const tokPacket = kural(
  /("(?:\\.|[^"\\])*"?)|(\b(?:0x[\da-fA-F]+|\d+(?:\.\d+)*)\b)|([A-Za-z_][\w.:-]*)|(\s+)|([^\s\w])/gy,
  [() => "str", () => "num", w => PACKET_WORDS.has(w) ? "kw" : w.includes(".") ? "self" : "", () => "", () => "op"]);
const AD_CMD = new Set("get-aduser get-adcomputer get-adgroup get-adgroupmember get-adobject get-adorganizationalunit -filter -ldapfilter -identity -searchbase -searchscope -properties -recursive -and -or -not -eq -ne -like -notlike -gt -ge -lt -le subtree onelevel base".split(" "));
const AD_ATTR = new Set("samaccountname objectclass objectcategory useraccountcontrol memberof member serviceprincipalname admincount badpwdcount logoncount pwdlastset mail department title description distinguishedname cn ou dc name dnshostname operatingsystem groupscope groupcategory enabled passwordneverexpires trustedfordelegation doesnotrequirepreauth passwordnotrequired".split(" "));
const tokAd = kural(
  /(#[^\n]*)|("(?:""|[^"])*"?|'(?:''|[^'])*'?)|(\\[0-9a-fA-F]{2}|\b1\.2\.840\.113556\.1\.4\.(?:803|804|1941)\b)|(\$true\b|\$false\b)|(\b\d+\b)|(-?[A-Za-z_][\w.-]*)|(\s+)|([^\s\w])/giy,
  [() => "com", () => "str", () => "dec", () => "const", () => "num",
   w => (AD_CMD.has(w.toLowerCase()) ? "kw" : AD_ATTR.has(w.toLowerCase()) ? "bi" : ""), () => "", () => "op"]);
const ASM_OP = new Set(("mov movzx movsx movsxd lea push pop add sub inc dec neg imul mul idiv div and or xor not shl shr sal sar rol ror " +
  "cmp test jmp je jz jne jnz jg jnle jge jnl jl jnge jle jng ja jnbe jae jnb jnc jb jnae jc jbe jna js jns jo jno " +
  "sete setz setne setnz setg setge setl setle seta setae setb setbe cmove cmovz cmovne cmovnz cmovg cmovge cmovl cmovle cmova cmovae cmovb cmovbe " +
  "call ret leave nop syscall int cdq cqo rep movsb stosb scasb").split(" "));
const ASM_REG = new Set(("rax rbx rcx rdx rsi rdi rbp rsp rip r8 r9 r10 r11 r12 r13 r14 r15 " +
  "eax ebx ecx edx esi edi ebp esp eip r8d r9d r10d r11d r12d r13d r14d r15d " +
  "ax bx cx dx si di bp sp r8w r9w r10w r11w r12w r13w r14w r15w " +
  "al bl cl dl ah bh ch dh sil dil bpl spl r8b r9b r10b r11b r12b r13b r14b r15b fs gs cs ds es ss rflags eflags").split(" "));
const ASM_DIR = new Set("byte word dword qword ptr offset short near far rel section global globl extern text data bss align db dw dd dq intel_syntax noprefix".split(" "));
const tokAsm = kural(
  /(;[^\n]*)|("(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(\.[A-Za-z_][\w.]*:?|\b[A-Za-z_]\w*:)|(\b0[xX][\da-fA-F]+\b|\b0[bB][01]+\b|\b\d+[\da-fA-F]*h\b|\b\d+\b)|([A-Za-z_]\w*)|(\s+)|([^\s\w])/giy,
  [() => "com", () => "str", () => "fn", () => "num",
   w => { const l = w.toLowerCase(); return ASM_OP.has(l) ? "kw" : ASM_REG.has(l) ? "self" : ASM_DIR.has(l) ? "bi" : ""; },
   () => "", () => "op"]);
const TOKENIZERS = { tshark: tokBash, "tcpdump-lab": tokBash, asm: tokAsm, x86: tokAsm, ad: tokAd, ldap: tokAd, packets: tokPacket, wireshark: tokPacket, bpf: tokPacket, cmd: tokCmd, batch: tokCmd, bat: tokCmd, kibana: tokElastic, lucene: tokElastic, eql: tokElastic, esql: tokElastic, ingest: tokJs, rule: tokJs, elastic: tokElastic, sigma: tokSigma, yaml: tokSigma, yara: tokYara, javascript: tokJs, js: tokJs, c: tokC, php: tokPhp, java: tokJava, csharp: tokCsharp, cs: tokCsharp, spl: tokSpl, splunk: tokSpl, kql: tokKql, kusto: tokKql, sql: tokSql, python: tokenize, py: tokenize, bash: tokBash, sh: tokBash, powershell: tokPs, ps: tokPs, regex: tokRegex };

// Satır satır HTML (editör ve kod blokları için): her satır ayrı dizi elemanı.
export function highlightLines(src, dil = "python") {
  const lines = [""];
  const tok = TOKENIZERS[dil];
  const parcalar = tok ? tok(src) : [["", src]];
  for (const [cls, text] of parcalar) {
    const parts = text.split("\n");
    parts.forEach((p, i) => {
      if (i > 0) lines.push("");
      if (p) lines[lines.length - 1] += cls ? `<span class="tok-${cls}">${esc(p)}</span>` : esc(p);
    });
  }
  return lines;
}
