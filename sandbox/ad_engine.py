# -*- coding: utf-8 -*-
"""Pafta · Active Directory ve RFC 4515 LDAP değerlendirici motoru.

Bu modül:
1. `tracks/ad/dizin.json` içindeki sahte ama gerçeğe sadık Active Directory
   dizinini (`DC=pafta,DC=local`) yükler ve geçişli (nested) grup üyeliklerini,
   hesaplanan AD özelliklerini (`Enabled`, `PasswordNeverExpires` vb.) hazırlar.
2. RFC 4515 uyumlu LDAP filtrelerini (`&`, `|`, `!`, `=`, `>=`, `<=`, `*` joker,
   `attr=*` varlık, `\2a`/`\28`/`\29`/`\5c` kaçışları ve `1.2.840.113556.1.4.803`,
   `804`, `1941` eşleştirme kuralları) ayrıştırır ve değerlendirir.
3. PowerShell ActiveDirectory modülünün `Get-ADUser`, `Get-ADComputer`,
   `Get-ADGroup`, `Get-ADGroupMember`, `Get-ADObject` ve `Get-ADOrganizationalUnit`
   komutlarını (`-Filter`, `-LDAPFilter`, `-Identity`, `-SearchBase`,
   `-SearchScope`, `-Properties`, `-Recursive`) gerçeğe sadık biçimde çalıştırır.
"""
import copy
import json
import os
import re
import shlex

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIZIN_YOLU = os.path.join(ROOT, "tracks", "ad", "dizin.json")
DOMAIN_DN = "DC=pafta,DC=local"

NUMERIC_ATTRS = {
    "useraccountcontrol",
    "admincount",
    "badpwdcount",
    "logoncount",
    "pwdlastset",
    "primarygroupid",
    "lastlogontimestamp",
    "accountexpires",
    "grouptype",
    "samaccounttype",
}

BOOL_ATTRS = {
    "enabled",
    "passwordneverexpires",
    "doesnotrequirepreauth",
    "trustedfordelegation",
    "passwordnotrequired",
}

# ActiveDirectory modülünün kendi özellik adları (yalnızca -Filter ve -Properties
# tarafında geçerlidir; ham LDAP filtresinde bu adlar öznitelik DEĞİLDİR).
ATTR_ALIASES = {
    "emailaddress": "mail",
    "serviceprincipalnames": "servicePrincipalName",
}

OID_BIT_AND = "1.2.840.113556.1.4.803"
OID_BIT_OR = "1.2.840.113556.1.4.804"
OID_IN_CHAIN = "1.2.840.113556.1.4.1941"

# DN sözdizimli öznitelikler: joker (*) alt dize araması desteklenmez
DN_ATTRS = {"member", "memberof", "distinguishedname", "manager", "objectcategory", "managedby"}

# Sınıf adı -> defaultObjectCategory (objectCategory kısa yazımı için)
DEFAULT_OBJECT_CATEGORY = {
    "user": "person",
    "contact": "person",
    "organizationalperson": "person",
    "inetorgperson": "person",
}


def _dn_norm(dn, strip_outer=True):
    s = dn.strip() if strip_outer else dn
    return re.sub(r"\s*([,=])\s*", r"\1", s)


class ADError(Exception):
    def __init__(self, msg, line=1):
        super().__init__(msg)
        self.msg = msg
        self.line = line


def load_raw_directory(path=DIZIN_YOLU):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Directory:
    """Bellek içi Active Directory dizini (`DC=pafta,DC=local`)."""

    def __init__(self, raw_objects=None):
        objs = copy.deepcopy(raw_objects if raw_objects is not None else load_raw_directory())
        self.objects = objs
        self.by_dn = {}
        for obj in self.objects:
            dn = obj.get("distinguishedName", "")
            self.by_dn[dn.casefold()] = obj
            self.by_dn[_dn_norm(dn.casefold())] = obj
        self._enrich()

    def _enrich(self):
        # member ve memberOf bağlantılarını iki yönlü eşitle
        for obj in self.objects:
            dn = obj.get("distinguishedName", "")
            for m_dn in (obj.get("member") or []):
                target = self.by_dn.get(m_dn.casefold())
                if target is not None:
                    m_of = target.setdefault("memberOf", [])
                    if not any(x.casefold() == dn.casefold() for x in m_of):
                        m_of.append(dn)
            for g_dn in (obj.get("memberOf") or []):
                grp = self.by_dn.get(g_dn.casefold())
                if grp is not None:
                    mem = grp.setdefault("member", [])
                    if not any(x.casefold() == dn.casefold() for x in mem):
                        mem.append(dn)

        # Her nesneye hesaplanan AD özelliklerini ve normalize anahtar tablosunu ekle
        for obj in self.objects:
            cat = str(obj.get("objectCategory") or "").casefold()
            if "sAMAccountType" not in obj:
                if cat == "person":
                    obj["sAMAccountType"] = 805306368
                elif cat == "computer":
                    obj["sAMAccountType"] = 805306369
                elif cat == "group":
                    obj["sAMAccountType"] = 268435456
            # Hesaplanan özellikler (Enabled vb.) gerçek AD'de LDAP özniteliği değildir;
            # ActiveDirectory modülü bunları userAccountControl'dan türetir. Bu yüzden
            # ayrı tutulur: ham LDAP filtresi onları görmez, -Properties çıktısı görür.
            comp = {}
            uac = obj.get("userAccountControl")
            if isinstance(uac, int):
                comp["enabled"] = (uac & 2) == 0
                comp["passwordneverexpires"] = (uac & 65536) != 0
                comp["passwordnotrequired"] = (uac & 32) != 0
                comp["trustedfordelegation"] = (uac & 524288) != 0
                comp["doesnotrequirepreauth"] = (uac & 4194304) != 0
            obj["_computed"] = comp
            obj["_map"] = {k.casefold(): k for k in obj.keys() if not k.startswith("_")}

    def get_attr(self, obj, attr_name, ps=False):
        """LDAP özniteliğini döndürür. ps=True ise ActiveDirectory modülünün
        hesaplanan özelliklerine ve takma adlarına (EmailAddress vb.) da bakar."""
        low = attr_name.casefold()
        if ps:
            if low in obj.get("_computed", {}):
                return obj["_computed"][low]
            low = ATTR_ALIASES.get(low, low).casefold()
        orig_key = obj.get("_map", {}).get(low)
        if orig_key is None:
            return None
        return obj.get(orig_key)

    def dn_exists(self, dn):
        low = dn.strip().casefold()
        if low == DOMAIN_DN.casefold():
            return True
        return low in self.by_dn

    def in_scope(self, obj, search_base, search_scope="Subtree"):
        scope_low = str(search_scope if search_scope is not None else "Subtree").strip().casefold()
        scope_map = {
            "base": "base", "0": "base",
            "onelevel": "onelevel", "1": "onelevel",
            "subtree": "subtree", "2": "subtree",
        }
        norm_scope = scope_map.get(scope_low)
        if norm_scope is None:
            raise ADError(f"Geçersiz -SearchScope değeri: '{search_scope}'. Base (0), OneLevel (1) veya Subtree (2) olmalı.")
        base_low = (search_base or DOMAIN_DN).strip().casefold()
        dn = obj.get("distinguishedName", "")
        dn_low = dn.casefold()
        if norm_scope == "base":
            return dn_low == base_low
        if norm_scope == "onelevel":
            if "," not in dn_low:
                return False
            parent_low = dn_low.split(",", 1)[1].strip()
            return parent_low == base_low
        return dn_low == base_low or dn_low.endswith("," + base_low)

    def transitive_attr_targets(self, obj, attr):
        """Verilen DN özniteliği (memberOf, member, manager, managedBy vb.) üzerinden
        zincirleme ulaşılabilen tüm normalize DN'leri (casefold) döndürür (1.2.840.113556.1.4.1941)."""
        visited = set()
        raw_vals = self.get_attr(obj, attr)
        if not raw_vals:
            return visited
        if not isinstance(raw_vals, list):
            raw_vals = [raw_vals]
        stack = [_dn_norm(str(v).casefold()) for v in raw_vals if v is not None]
        while stack:
            cur_dn = stack.pop()
            if cur_dn in visited:
                continue
            visited.add(cur_dn)
            target_obj = self.by_dn.get(cur_dn)
            if target_obj is not None:
                next_vals = self.get_attr(target_obj, attr)
                if next_vals:
                    if not isinstance(next_vals, list):
                        next_vals = [next_vals]
                    for nv in next_vals:
                        if nv is not None:
                            n_low = _dn_norm(str(nv).casefold())
                            if n_low not in visited:
                                stack.append(n_low)
        return visited

    def transitive_member_of(self, obj):
        """Nesnenin doğrudan ve dolaylı (iç içe) üye olduğu tüm grup DN'lerini (casefold) döndürür."""
        visited = set()
        stack = [dn.casefold() for dn in (self.get_attr(obj, "memberOf") or [])]
        while stack:
            g_dn = stack.pop()
            if g_dn in visited:
                continue
            visited.add(g_dn)
            g_obj = self.by_dn.get(g_dn)
            if g_obj:
                for parent_dn in (self.get_attr(g_obj, "memberOf") or []):
                    p_low = parent_dn.casefold()
                    if p_low not in visited:
                        stack.append(p_low)
        return visited

    def transitive_members(self, group_obj):
        """Grubun doğrudan ve dolaylı tüm üye DN'lerini (casefold) döndürür."""
        visited = set()
        stack = [dn.casefold() for dn in (self.get_attr(group_obj, "member") or [])]
        while stack:
            m_dn = stack.pop()
            if m_dn in visited:
                continue
            visited.add(m_dn)
            m_obj = self.by_dn.get(m_dn)
            if m_obj and str(self.get_attr(m_obj, "objectCategory") or "").casefold() == "group":
                for child_dn in (self.get_attr(m_obj, "member") or []):
                    c_low = child_dn.casefold()
                    if c_low not in visited:
                        stack.append(c_low)
        return visited


# ── RFC 4515 LDAP FİLTRE AYRIŞTIRICISI VE DEĞERLENDİRİCİSİ ────────────────────

def _decode_ldap_hex(segment, line=1):
    """RFC 4515 kaçışlarını (\2a, \28, \29, \5c vb.) çözer. Kaçışsız ( veya ) ya da bozuk \ hata verir."""
    out = bytearray()
    i = 0
    n = len(segment)
    while i < n:
        ch = segment[i]
        if ch in ("(", ")"):
            raise ADError(
                f"LDAP değerinde kaçışsız '{ch}' kullanılamaz; '\\28' ve '\\29' kullanın.",
                line=line,
            )
        if ch == "\\":
            if i + 2 >= n or not re.fullmatch(r"[0-9a-fA-F]{2}", segment[i + 1 : i + 3]):
                raise ADError(
                    "Geçersiz LDAP kaçış dizisi: '\\' karakterinden sonra iki onaltılık basamak gelmelidir (ör. \\2a, \\28, \\29, \\5c).",
                    line=line,
                )
            out.append(int(segment[i + 1 : i + 3], 16))
            i += 3
        else:
            out.extend(ch.encode("utf-8"))
            i += 1
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ADError(f"Geçersiz UTF-8 LDAP kaçış dizisi: {exc}", line=line)


def _parse_assertion_value(raw_val, allow_wildcards=False, line=1):
    if raw_val == "":
        return ("exact", "")
    if allow_wildcards:
        if raw_val == "*":
            return ("present", None)
        # Kaçışsız '*' karakterlerine göre böl (\2a bir '*' değildir, zaten '2a' olarak yazılır)
        parts = raw_val.split("*")
        decoded_parts = [_decode_ldap_hex(p, line=line) for p in parts]
        if len(decoded_parts) == 1:
            return ("exact", decoded_parts[0])
        return ("substring", decoded_parts)
    else:
        if "*" in raw_val:
            raise ADError(
                "Bu karşılaştırma işlecinde joker '*' kullanılamaz (yalnızca '=' içinde geçerlidir).",
                line=line,
            )
        return ("exact", _decode_ldap_hex(raw_val, line=line))


def parse_ldap_filter(text, line=1):
    """RFC 4515 LDAP filtresini AST'ye çevirir."""
    s = text.strip()
    if not s:
        raise ADError("LDAP filtresi boş olamaz.", line=line)
    if not (s.startswith("(") and s.endswith(")")):
        raise ADError("RFC 4515 LDAP filtresi '(' ile başlamalı ve ')' ile bitmelidir.", line=line)

    node, pos = _parse_filter_at(s, 0, line=line)
    while pos < len(s) and s[pos].isspace():
        pos += 1
    if pos != len(s):
        raise ADError(f"LDAP filtresinin sonunda fazladan karakter var: {s[pos:]!r}", line=line)
    return node


def _parse_filter_at(s, pos, line=1):
    n = len(s)
    while pos < n and s[pos].isspace():
        pos += 1
    if pos >= n or s[pos] != "(":
        raise ADError("LDAP filtresinde '(' bekleniyordu.", line=line)
    pos += 1
    if pos >= n:
        raise ADError("Kapanmamış '(' parantezi.", line=line)
    if s[pos].isspace():
        raise ADError("RFC 4515 LDAP filtresinde '(' karakterinden hemen sonra boşluk gelemez.", line=line)

    op = s[pos]
    if op in ("&", "|"):
        pos += 1
        children = []
        while True:
            while pos < n and s[pos].isspace():
                pos += 1
            if pos >= n:
                raise ADError(f"'({op}' bloğu ')' ile kapatılmamış.", line=line)
            if s[pos] == ")":
                pos += 1
                break
            child, pos = _parse_filter_at(s, pos, line=line)
            children.append(child)
        if not children:
            raise ADError(f"'({op})' içinde en az bir alt filtre bulunmalıdır.", line=line)
        return ("and" if op == "&" else "or", children), pos

    if op == "!":
        pos += 1
        while pos < n and s[pos].isspace():
            pos += 1
        if pos >= n or s[pos] != "(":
            raise ADError("'(!' sonrasında parantez içinde bir alt filtre gelmelidir: '(!(alan=deger))'.", line=line)
        child, pos = _parse_filter_at(s, pos, line=line)
        while pos < n and s[pos].isspace():
            pos += 1
        if pos >= n or s[pos] != ")":
            raise ADError(
                "'(!' (DEĞİL) işleci tam olarak tek bir alt filtre alır; birden fazla koşul için '(!(&...))' veya '(!(|...))' kullanın.",
                line=line,
            )
        pos += 1
        return ("not", child), pos

    # Basit filtre öğesi: ')' karakterine kadar oku (ancak içerde '(' varsa hata).
    # RFC 4515 gereği öznitelik adından önce/sonra veya değerin sonunda boşluk kırpılmaz!
    start = pos
    while pos < n and s[pos] != ")":
        if s[pos] == "(":
            raise ADError(
                "Basit filtre içinde kaçışsız '(' bulundu. Mantıksal işleç (&, |, !) eksik olabilir veya değerde '\\28' kullanılmalıdır.",
                line=line,
            )
        pos += 1
    if pos >= n or s[pos] != ")":
        raise ADError("LDAP filtresinde kapanış ')' parantezi eksik.", line=line)
    item_str = s[start:pos]
    pos += 1
    if not item_str:
        raise ADError("Boş filtre '()' geçersizdir.", line=line)
    return _parse_simple_item(item_str, line=line), pos


_SIMPLE_ITEM_RE = re.compile(
    r"^([A-Za-z][A-Za-z0-9-]*)(?::([A-Za-z0-9.-]+(?::[A-Za-z0-9.-]+)*))?(:=|>=|<=|~=|=[><]?|[><])(.*)$",
    re.S,
)


def _parse_simple_item(item_str, line=1):
    m = _SIMPLE_ITEM_RE.match(item_str)
    if not m:
        if ">" in item_str or "<" in item_str:
            raise ADError(
                "RFC 4515 LDAP filtrelerinde '>' veya '<' işleci yoktur; yalnızca '>=' ve '<=' kullanılır (kesin küçüklük için '(!(alan>=deger))' yazın).",
                line=line,
            )
        raise ADError(
            f"LDAP filtresinde geçerli bir 'öznitelik=değer' karşılaştırması bulunamadı: {item_str!r}",
            line=line,
        )
    attr, ext_part, op, rhs = m.groups()
    if op in (">", "<", "=>", "=<"):
        raise ADError(
            f"RFC 4515 LDAP filtrelerinde '{op}' işleci yoktur; yalnızca '>=' ve '<=' kullanılır (kesin küçüklük için '(!(alan>=deger))' yazın).",
            line=line,
        )
    if op == ":=":
        if not ext_part:
            raise ADError("':=' genişletilmiş eşleştirmesinde OID belirtilmelidir (ör. alan:1.2.840.113556.1.4.803:=2).", line=line)
        oid = ext_part.split(":")[-1].strip()
        if oid not in (OID_BIT_AND, OID_BIT_OR, OID_IN_CHAIN):
            raise ADError(f"Desteklenmeyen veya geçersiz LDAP eşleştirme OID'si: '{oid}'.", line=line)
        kind, val = _parse_assertion_value(rhs, allow_wildcards=False, line=line)
        return ("ext", attr, oid, val)

    if ext_part is not None:
        raise ADError(f"OID uzantısı ('{ext_part}') yalnızca ':=' işleciyle kullanılabilir, '{op}' ile kullanılamaz.", line=line)
    kind, val = _parse_assertion_value(rhs, allow_wildcards=(op == "="), line=line)
    if op == "=" and kind == "present":
        return ("present", attr)
    if op == "=" and kind == "substring":
        return ("substring", attr, val)
    return ("cmp", op, attr, val)


def _values_of(directory, obj, attr):
    val = directory.get_attr(obj, attr)
    if val is None:
        return []
    if isinstance(val, list):
        return [v for v in val if v is not None]
    return [val]


def _substring_match(candidate_str, parts):
    """parts = [initial, any1, ..., final] (case-insensitive)."""
    cand = candidate_str.casefold()
    segs = [p.casefold() for p in parts]
    # initial
    if segs[0]:
        if not cand.startswith(segs[0]):
            return False
        pos = len(segs[0])
    else:
        pos = 0
    # final
    if segs[-1]:
        if not cand.endswith(segs[-1]):
            return False
        end_limit = len(cand) - len(segs[-1])
        if end_limit < pos:
            return False
    else:
        end_limit = len(cand)
    # middle segments
    for mid in segs[1:-1]:
        if not mid:
            continue
        idx = cand.find(mid, pos, end_limit)
        if idx == -1:
            return False
        pos = idx + len(mid)
    return True


def _compare_single(cand, op, target_str, attr_low, line=1):
    if attr_low in BOOL_ATTRS or isinstance(cand, bool):
        t_low = target_str.casefold()
        if t_low in ("true", "$true", "1"):
            t_bool = True
        elif t_low in ("false", "$false", "0"):
            t_bool = False
        else:
            return False
        c_bool = bool(cand)
        if op in ("=", "~="):
            return c_bool == t_bool
        return False

    if attr_low in NUMERIC_ATTRS or isinstance(cand, int):
        if target_str != target_str.strip():
            raise ADError(f"'{attr_low}' sayısal alanı için boşluksuz tam sayı değer bekleniyordu: {target_str!r}", line=line)
        try:
            c_num = int(cand)
            t_num = int(target_str)
        except ValueError:
            raise ADError(f"'{attr_low}' sayısal alanı için tam sayı değer bekleniyordu: {target_str!r}", line=line)
        if op in ("=", "~="):
            return c_num == t_num
        if op == ">=":
            return c_num >= t_num
        if op == "<=":
            return c_num <= t_num
        return False

    c_str = str(cand).casefold()
    t_str = target_str.casefold()
    if attr_low == "objectcategory":
        # Gerçek AD, objectCategory değerini sınıfın defaultObjectCategory'sine çevirir:
        # (objectCategory=user) ve (objectCategory=contact) ikisi de CN=Person olur.
        if t_str.startswith("cn="):
            t_str = t_str.split(",", 1)[0][3:].strip()
        t_str = t_str.replace("-", "")
        t_str = DEFAULT_OBJECT_CATEGORY.get(t_str, t_str)
        c_str = c_str.replace("-", "")
        return op in ("=", "~=") and c_str == t_str
    if attr_low in DN_ATTRS:
        c_str = _dn_norm(c_str, strip_outer=True)
        t_str = _dn_norm(t_str, strip_outer=False)
    if op in ("=", "~="):
        return c_str == t_str
    if op == ">=":
        return c_str >= t_str
    if op == "<=":
        return c_str <= t_str
    return False


def eval_ldap_ast(ast_node, directory, obj, line=1):
    kind = ast_node[0]
    if kind == "and":
        return all(eval_ldap_ast(c, directory, obj, line=line) for c in ast_node[1])
    if kind == "or":
        return any(eval_ldap_ast(c, directory, obj, line=line) for c in ast_node[1])
    if kind == "not":
        return not eval_ldap_ast(ast_node[1], directory, obj, line=line)
    if kind == "present":
        attr = ast_node[1]
        vals = _values_of(directory, obj, attr)
        return len(vals) > 0
    if kind == "substring":
        _, attr, parts = ast_node
        if attr.casefold() in DN_ATTRS:
            # Gerçek AD: DN sözdizimli özniteliklerde (member, memberOf, distinguishedName,
            # objectCategory, manager) joker desteklenmez; filtre hata vermez ama hiçbir şey eşleşmez.
            return False
        vals = _values_of(directory, obj, attr)
        return any(_substring_match(str(v), parts) for v in vals)
    if kind == "cmp":
        _, op, attr, target = ast_node
        attr_low = attr.casefold()
        vals = _values_of(directory, obj, attr)
        return any(_compare_single(v, op, target, attr_low, line=line) for v in vals)
    if kind == "ext":
        _, attr, oid, target = ast_node
        attr_low = attr.casefold()
        if oid in (OID_BIT_AND, OID_BIT_OR):
            if target != target.strip():
                raise ADError(f"Bit eşleştirme kuralında ({oid}) boşluksuz tam sayı maske bekleniyordu: {target!r}", line=line)
            try:
                mask = int(target)
            except ValueError:
                raise ADError(f"Bit eşleştirme kuralında ({oid}) tam sayı maske bekleniyordu: {target!r}", line=line)
            vals = _values_of(directory, obj, attr)
            for v in vals:
                try:
                    iv = int(v)
                except ValueError:
                    continue
                if oid == OID_BIT_AND and (iv & mask) == mask:
                    return True
                if oid == OID_BIT_OR and (iv & mask) != 0:
                    return True
            return False
        if oid == OID_IN_CHAIN:
            if target != target.strip():
                return False
            target_dn = _dn_norm(target.casefold(), strip_outer=False)
            return target_dn in directory.transitive_attr_targets(obj, attr)
    raise ADError(f"Bilinmeyen filtre düğümü: {kind}", line=line)


# ── POWERSHELL -Filter AYRIŞTIRICISI VE LDAP'A ÇEVİRİCİ ───────────────────────

_PS_TOKEN_RE = re.compile(
    r"""\s*(?:(\()|(\))|("(?:""|[^"])*"|'(?:''|[^'])*')|(-(?:and|or|not|eq|ne|like|notlike|gt|ge|lt|le)\b)|(\$true\b|\$false\b|\*)|([A-Za-z_][A-Za-z0-9_.-]*|[+-]?\d+))""",
    re.I,
)


def _escape_ldap_literal(val, keep_wildcards=False):
    out = []
    for ch in str(val):
        if ch == "\\":
            out.append("\\5c")
        elif ch == "(":
            out.append("\\28")
        elif ch == ")":
            out.append("\\29")
        elif ch == "\x00":
            out.append("\\00")
        elif ch == "*" and not keep_wildcards:
            out.append("\\2a")
        else:
            out.append(ch)
    return "".join(out)


def translate_ps_filter_to_ldap(ps_filter_str, line=1):
    """PowerShell -Filter ifadesini eşdeğer RFC 4515 LDAP filtresine çevirir."""
    s = ps_filter_str.strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1].strip()
    if not s:
        raise ADError("-Filter parametresi boş olamaz.", line=line)
    if s == "*":
        return "(objectClass=*)"

    tokens = []
    pos = 0
    while pos < len(s):
        m = _PS_TOKEN_RE.match(s, pos)
        if not m:
            raise ADError(f"-Filter sözdizimi hatası (konum {pos + 1}): {s[pos:pos+20]!r}", line=line)
        pos = m.end()
        lp, rp, qstr, op, kw, ident = m.groups()
        if lp:
            tokens.append(("LP", "("))
        elif rp:
            tokens.append(("RP", ")"))
        elif qstr:
            if qstr.startswith('"'):
                val = qstr[1:-1].replace('""', '"')
            else:
                val = qstr[1:-1].replace("''", "'")
            tokens.append(("VAL", val))
        elif op:
            tokens.append(("OP", op.lower()))
        elif kw:
            tokens.append(("VAL", kw))
        elif ident:
            low = ident.lower()
            if low in ("and", "or", "not", "eq", "ne", "like", "notlike", "gt", "ge", "lt", "le"):
                tokens.append(("OP", "-" + low))
            else:
                tokens.append(("IDENT", ident))

    idx = 0

    def parse_or():
        nonlocal idx
        left = parse_and()
        items = [left]
        while idx < len(tokens) and tokens[idx] == ("OP", "-or"):
            idx += 1
            items.append(parse_and())
        return items[0] if len(items) == 1 else "(|" + "".join(items) + ")"

    def parse_and():
        nonlocal idx
        left = parse_not()
        items = [left]
        while idx < len(tokens) and tokens[idx] == ("OP", "-and"):
            idx += 1
            items.append(parse_not())
        return items[0] if len(items) == 1 else "(&" + "".join(items) + ")"

    def parse_not():
        nonlocal idx
        if idx < len(tokens) and tokens[idx] == ("OP", "-not"):
            idx += 1
            sub = parse_not()
            return f"(!{sub})"
        return parse_primary()

    def parse_primary():
        nonlocal idx
        if idx >= len(tokens):
            raise ADError("-Filter ifadesi beklenmedik biçimde sona erdi.", line=line)
        if tokens[idx][0] == "LP":
            idx += 1
            inner = parse_or()
            if idx >= len(tokens) or tokens[idx][0] != "RP":
                raise ADError("-Filter içinde kapanmamış '(' parantezi.", line=line)
            idx += 1
            return inner
        if tokens[idx][0] != "IDENT":
            raise ADError(f"-Filter içinde özellik adı bekleniyordu, {tokens[idx][1]!r} geldi.", line=line)
        prop = tokens[idx][1]
        idx += 1
        if idx >= len(tokens) or tokens[idx][0] != "OP" or tokens[idx][1] in ("-and", "-or", "-not"):
            raise ADError(f"'{prop}' özelliğinden sonra karşılaştırma işleci (-eq, -ne, -like, -ge, -le vb.) bekleniyordu.", line=line)
        cmp_op = tokens[idx][1]
        idx += 1
        if idx >= len(tokens) or tokens[idx][0] not in ("VAL", "IDENT"):
            raise ADError(f"'{prop} {cmp_op}' sonrasında bir değer bekleniyordu.", line=line)
        raw_val = tokens[idx][1]
        idx += 1
        return _ps_comparison_to_ldap(prop, cmp_op, raw_val, line=line)

    res = parse_or()
    if idx != len(tokens):
        raise ADError(f"-Filter sonunda beklenmeyen ifade: {tokens[idx][1]!r}", line=line)
    return res


def _ps_comparison_to_ldap(prop, cmp_op, raw_val, line=1):
    p_low = prop.casefold()
    v_low = str(raw_val).strip().casefold()

    # Hesaplanan boolean UAC bayrakları (Enabled, PasswordNeverExpires vb.)
    uac_bit_map = {
        "enabled": (2, True),                  # Enabled=$true -> bit 2 KAPALI
        "passwordneverexpires": (65536, False),
        "passwordnotrequired": (32, False),
        "trustedfordelegation": (524288, False),
        "doesnotrequirepreauth": (4194304, False),
    }
    if p_low in uac_bit_map and cmp_op not in ("-eq", "-ne"):
        raise ADError(f"'{prop}' bir $true/$false özelliğidir; yalnızca -eq ve -ne ile karşılaştırılır.", line=line)
    if p_low in uac_bit_map:
        bit, invert_for_true = uac_bit_map[p_low]
        if v_low in ("$true", "true", "1"):
            want_true = True
        elif v_low in ("$false", "false", "0"):
            want_true = False
        else:
            raise ADError(f"'{prop}' özelliği için $true veya $false bekleniyordu.", line=line)
        if cmp_op == "-ne":
            want_true = not want_true
        bit_set_filter = f"(userAccountControl:{OID_BIT_AND}:={bit})"
        if invert_for_true:
            return f"(!{bit_set_filter})" if want_true else bit_set_filter
        else:
            return bit_set_filter if want_true else f"(!{bit_set_filter})"

    # Modülün takma adlarını (EmailAddress -> mail) LDAP adına çevir
    prop = ATTR_ALIASES.get(p_low, prop)

    if cmp_op == "-eq":
        # about_ActiveDirectory_Filter, LDAP Special Characters: '*' in
        # -eq/-ne STRING data is literal; wildcard comparisons use -like.
        return f"({prop}={_escape_ldap_literal(raw_val, keep_wildcards=False)})"
    if cmp_op == "-ne":
        return f"(!({prop}={_escape_ldap_literal(raw_val, keep_wildcards=False)}))"
    if cmp_op == "-like":
        if raw_val == "*":
            return f"({prop}=*)"
        return f"({prop}={_escape_ldap_literal(raw_val, keep_wildcards=True)})"
    if cmp_op == "-notlike":
        if raw_val == "*":
            return f"(!({prop}=*))"
        return f"(!({prop}={_escape_ldap_literal(raw_val, keep_wildcards=True)}))"
    if cmp_op == "-ge":
        return f"({prop}>={_escape_ldap_literal(raw_val)})"
    if cmp_op == "-le":
        return f"({prop}<={_escape_ldap_literal(raw_val)})"
    if cmp_op == "-gt":
        v = _escape_ldap_literal(raw_val)
        return f"(!({prop}<={v}))"
    if cmp_op == "-lt":
        v = _escape_ldap_literal(raw_val)
        return f"(!({prop}>={v}))"
    raise ADError(f"Desteklenmeyen -Filter işleci: {cmp_op}", line=line)


# ── GET-AD* KOMUT AYRIŞTIRICISI VE ÇALIŞTIRICISI ──────────────────────────────

CMDLET_CLASS_FILTER = {
    "get-aduser": "(&(objectCategory=person)(objectClass=user))",
    "get-adcomputer": "(objectCategory=computer)",
    "get-adgroup": "(objectCategory=group)",
    "get-adorganizationalunit": "(objectCategory=organizationalUnit)",
    "get-adobject": "(objectClass=*)",
}


def _tokenize_ps_command(cmd_text, line=1):
    """PowerShell komut satırını tırnakları ve { ... } bloklarını koruyarak parçalar."""
    tokens = []
    i = 0
    n = len(cmd_text)
    while i < n:
        while i < n and cmd_text[i].isspace():
            i += 1
        if i >= n:
            break
        ch = cmd_text[i]
        if ch in ("'", '"'):
            quote = ch
            i += 1
            buf = []
            while i < n:
                if cmd_text[i] == quote:
                    if i + 1 < n and cmd_text[i + 1] == quote:
                        buf.append(quote)
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(cmd_text[i])
                i += 1
            else:
                raise ADError(f"Kapanmamış {quote} tırnağı.", line=line)
            tokens.append("".join(buf))
        elif ch == "{":
            depth = 0
            start = i
            while i < n:
                if cmd_text[i] == "{":
                    depth += 1
                elif cmd_text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
            if depth != 0:
                raise ADError("Kapanmamış '{' bloğu.", line=line)
            tokens.append(cmd_text[start:i])
        else:
            start = i
            while i < n and not cmd_text[i].isspace() and cmd_text[i] not in (",",):
                i += 1
            tok = cmd_text[start:i]
            if tok:
                tokens.append(tok)
            if i < n and cmd_text[i] == ",":
                tokens.append(",")
                i += 1
    return tokens


def _parse_cmdlet_statement(stmt_text, line=1):
    tokens = _tokenize_ps_command(stmt_text, line=line)
    if not tokens:
        raise ADError("Boş komut.", line=line)
    cmd = tokens[0].lower()
    if cmd not in CMDLET_CLASS_FILTER and cmd != "get-adgroupmember":
        raise ADError(
            f"Bilinmeyen komut: '{tokens[0]}'. Geçerli komutlar: Get-ADUser, Get-ADComputer, Get-ADGroup, Get-ADGroupMember, Get-ADObject, Get-ADOrganizationalUnit veya doğrudan '(...)' LDAP filtresi.",
            line=line,
        )

    params = {
        "cmd": cmd,
        "identity": None,
        "filter": None,
        "ldapfilter": None,
        "searchbase": None,
        "searchscope": "Subtree",
        "properties": [],
        "recursive": False,
    }

    i = 1
    n = len(tokens)
    while i < n:
        t = tokens[i]
        t_low = t.lower()
        if t_low == "-recursive":
            if cmd != "get-adgroupmember":
                raise ADError("-Recursive parametresi yalnızca Get-ADGroupMember ile kullanılır.", line=line)
            params["recursive"] = True
            i += 1
        elif t_low in ("-identity", "-filter", "-ldapfilter", "-searchbase", "-searchscope"):
            if i + 1 >= n:
                raise ADError(f"'{t}' parametresi için değer eksik.", line=line)
            params[t_low[1:]] = tokens[i + 1]
            i += 2
        elif t_low == "-properties":
            if i + 1 >= n:
                raise ADError("'-Properties' parametresi için en az bir özellik adı gerekli.", line=line)
            i += 1
            props = []
            while i < n and not tokens[i].startswith("-"):
                if tokens[i] != ",":
                    for p in tokens[i].split(","):
                        if p.strip():
                            props.append(p.strip())
                i += 1
            if not props:
                raise ADError("'-Properties' parametresi için özellik adı belirtilmedi.", line=line)
            params["properties"] = props
        elif t.startswith("-"):
            raise ADError(f"Desteklenmeyen parametre: '{t}'.", line=line)
        else:
            if params["identity"] is None:
                params["identity"] = t
                i += 1
            else:
                raise ADError(f"Beklenmeyen konumsal argüman: '{t}'.", line=line)
    return params


def _execute_statement(stmt_text, directory, line=1):
    s = stmt_text.strip()
    # Doğrudan RFC 4515 LDAP filtresi mi?
    if s.startswith("("):
        ast_node = parse_ldap_filter(s, line=line)
        matched = [obj for obj in directory.objects if eval_ldap_ast(ast_node, directory, obj, line=line)]
        return {
            "baslik": f"LDAP · {s}",
            "objects": matched,
            "properties": [],
            "effective_ldap": s,
            "search_base": DOMAIN_DN,
            "search_scope": "Subtree",
        }

    p = _parse_cmdlet_statement(s, line=line)
    cmd = p["cmd"]

    if p["searchbase"] and not directory.dn_exists(p["searchbase"]):
        raise ADError(f"-SearchBase dizinde bulunamadı: '{p['searchbase']}'.", line=line)

    if cmd == "get-adgroupmember":
        if not p["identity"]:
            raise ADError("Get-ADGroupMember için -Identity (grup adı veya DN) belirtilmelidir.", line=line)
        if p["filter"] or p["ldapfilter"]:
            raise ADError("Get-ADGroupMember -Filter veya -LDAPFilter almaz; -Identity kullanın.", line=line)
        id_low = p["identity"].strip().casefold()
        target_group = None
        # Gerçek AD gibi: -Identity DN, GUID, SID veya sAMAccountName kabul eder (görünen ad değil)
        for obj in directory.objects:
            if str(directory.get_attr(obj, "objectCategory") or "").casefold() != "group":
                continue
            for key in ("sAMAccountName", "distinguishedName"):
                val = directory.get_attr(obj, key)
                if val and str(val).casefold() == id_low:
                    target_group = obj
                    break
            if target_group:
                break
        if not target_group:
            raise ADError(f"Grup bulunamadı: '{p['identity']}'.", line=line)

        if not p["recursive"]:
            member_dns = {dn.casefold() for dn in (directory.get_attr(target_group, "member") or [])}
            matched = [
                obj for obj in directory.objects
                if str(directory.get_attr(obj, "distinguishedName") or "").casefold() in member_dns
            ]
            eff_ldap = f"(memberOf={target_group['distinguishedName']})"
        else:
            all_member_dns = directory.transitive_members(target_group)
            matched = [
                obj for obj in directory.objects
                if str(directory.get_attr(obj, "distinguishedName") or "").casefold() in all_member_dns
                and str(directory.get_attr(obj, "objectCategory") or "").casefold() != "group"
            ]
            eff_ldap = f"(&(!(objectCategory=group))(memberOf:{OID_IN_CHAIN}:={target_group['distinguishedName']}))"

        return {
            "baslik": f"Get-ADGroupMember · {target_group['sAMAccountName']}" + (" (-Recursive)" if p["recursive"] else ""),
            "objects": matched,
            "properties": p["properties"],
            "effective_ldap": eff_ldap,
            "search_base": target_group["distinguishedName"],
            "search_scope": "Recursive" if p["recursive"] else "Direct",
        }

    # Get-ADUser, Get-ADComputer, Get-ADGroup, Get-ADObject, Get-ADOrganizationalUnit
    if sum(bool(x) for x in (p["identity"], p["filter"], p["ldapfilter"])) == 0:
        raise ADError(f"{cmd} için -Filter, -LDAPFilter veya -Identity belirtilmelidir.", line=line)
    if sum(bool(x) for x in (p["identity"], p["filter"], p["ldapfilter"])) > 1:
        raise ADError("-Identity, -Filter ve -LDAPFilter aynı komutta birlikte kullanılamaz.", line=line)

    base_class_ldap = CMDLET_CLASS_FILTER[cmd]
    if p["ldapfilter"]:
        user_ldap = p["ldapfilter"].strip()
        parse_ldap_filter(user_ldap, line=line)
    elif p["filter"]:
        user_ldap = translate_ps_filter_to_ldap(p["filter"], line=line)
    else:
        ident_esc = _escape_ldap_literal(p["identity"].strip())
        if cmd in ("get-adobject", "get-adorganizationalunit"):
            user_ldap = f"(distinguishedName={ident_esc})"
        else:
            user_ldap = f"(|(sAMAccountName={ident_esc})(distinguishedName={ident_esc}))"

    if base_class_ldap == "(objectClass=*)":
        effective_ldap = user_ldap
    elif user_ldap == "(objectClass=*)":
        effective_ldap = base_class_ldap
    else:
        effective_ldap = f"(&{base_class_ldap}{user_ldap})"

    ast_node = parse_ldap_filter(effective_ldap, line=line)
    matched = [
        obj for obj in directory.objects
        if directory.in_scope(obj, p["searchbase"], p["searchscope"])
        and eval_ldap_ast(ast_node, directory, obj, line=line)
    ]
    if p["identity"] and not matched:
        raise ADError(
            f"'{p['identity']}' kimliğine sahip bir nesne bulunamadı. -Identity görünen adı (ör. 'Ali Kaya') değil, "
            "sAMAccountName veya distinguishedName bekler; gerçek AD de burada hata fırlatır.",
            line=line,
        )
    return {
        "baslik": s,
        "objects": matched,
        "properties": p["properties"],
        "effective_ldap": effective_ldap,
        "search_base": p["searchbase"] or DOMAIN_DN,
        "search_scope": p["searchscope"] or "Subtree",
    }


def split_statements(code):
    """Yorumları temizler ve kodu bağımsız LDAP filtrelerine veya Get-AD* komutlarına ayırır."""
    clean_lines = []
    for idx, line in enumerate(code.replace("\r\n", "\n").split("\n"), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            clean_lines.append((idx, ""))
        else:
            clean_lines.append((idx, stripped))

    statements = []
    buf = []
    start_line = 1
    paren_depth = 0
    for idx, text in clean_lines:
        if not text:
            if buf and paren_depth <= 0:
                statements.append((start_line, " ".join(buf)))
                buf = []
                paren_depth = 0
            continue
        if not buf:
            start_line = idx
        buf.append(text)
        # Parantez derinliğini kaba olarak takip et (çok satırlı LDAP filtreleri için)
        if buf[0].startswith("("):
            for ch in text:
                if ch == "(":
                    paren_depth += 1
                elif ch == ")":
                    paren_depth -= 1
            if paren_depth <= 0:
                statements.append((start_line, "".join(buf)))
                buf = []
                paren_depth = 0
        else:
            statements.append((start_line, " ".join(buf)))
            buf = []
            paren_depth = 0

    if buf:
        statements.append((start_line, "".join(buf) if buf[0].startswith("(") else " ".join(buf)))
    return statements


def _format_attr_val(val):
    if val is None:
        return ""
    if isinstance(val, bool):
        return "True" if val else "False"
    if isinstance(val, list):
        # DN'ler virgül içerdiği için çok değerli öznitelikler ';' ile ayrılır
        return ";".join(str(x) for x in val)
    return str(val)


def _object_id(directory, obj):
    sam = directory.get_attr(obj, "sAMAccountName")
    if sam:
        return str(sam)
    name = directory.get_attr(obj, "name") or directory.get_attr(obj, "ou") or directory.get_attr(obj, "cn")
    return str(name or "")


def execute_code(code, raw_directory=None):
    directory = Directory(raw_directory)
    stmts = split_statements(code or "")
    if not stmts:
        return {"status": "ok", "segs": [], "tablolar": [], "results": [], "error": None}

    tablolar = []
    out_lines = []
    results = []

    try:
        for line_no, stmt in stmts:
            res = _execute_statement(stmt, directory, line=line_no)
            objs = res["objects"]
            props = res["properties"]
            explicit_props = [p for p in props if p != "*"]

            # Metin çıktısı:
            # - Açıkça -Properties p1, p2 verildiyse: sAMAccountName|p1|p2
            # - Aksi hâlde: her eşleşen nesne için sAMAccountName (veya OU için name)
            for obj in objs:
                oid = _object_id(directory, obj)
                if explicit_props:
                    row_vals = [oid] + [_format_attr_val(directory.get_attr(obj, p, ps=True)) for p in explicit_props]
                    out_lines.append("|".join(row_vals))
                else:
                    out_lines.append(oid)

            # Görsel tablo sütunları
            if "*" in props:
                cols = ["sAMAccountName", "objectCategory", "Enabled", "userAccountControl", "adminCount", "badPwdCount", "servicePrincipalName", "distinguishedName"]
            elif explicit_props:
                cols = ["sAMAccountName"] + explicit_props
            else:
                cols = ["sAMAccountName", "name", "Enabled", "distinguishedName"]

            satirlar = []
            for obj in objs:
                row = []
                for c in cols:
                    if c.lower() == "samaccountname":
                        row.append(_object_id(directory, obj))
                    else:
                        row.append(_format_attr_val(directory.get_attr(obj, c, ps=True)))
                satirlar.append(row)

            tablolar.append({"baslik": res["baslik"], "sutunlar": cols, "satirlar": satirlar})
            results.append(res)
    except ADError as exc:
        return {
            "status": "error",
            "error": {"type": "ADHatası", "msg": exc.msg, "line": exc.line, "frames": [], "where": "kod"},
            "segs": [],
            "tablolar": [],
            "results": [],
        }

    cikti = ("\n".join(out_lines) + "\n") if out_lines else ""
    return {
        "status": "ok",
        "segs": [["out", cikti]] if cikti else [],
        "tablolar": tablolar,
        "kql": True,
        "results": results,
        "error": None,
    }


def explain_ldap(code):
    """Tezgahtaki 'LDAP' düğmesi için her ifadenin etkin RFC 4515 LDAP karşılığını üretir."""
    directory = Directory()
    stmts = split_statements(code or "")
    if not stmts:
        return {"status": "ok", "text": "(çevrilecek LDAP filtresi veya Get-AD* komutu yok)"}
    blocks = []
    try:
        for line_no, stmt in stmts:
            res = _execute_statement(stmt, directory, line=line_no)
            blocks.append(
                f"# satır {line_no}: {stmt}\n"
                f"SearchBase  : {res['search_base']}\n"
                f"SearchScope : {res['search_scope']}\n"
                f"LDAPFilter  : {res['effective_ldap']}"
            )
    except ADError as exc:
        return {
            "status": "error",
            "error": {"type": "ADHatası", "msg": exc.msg, "line": exc.line, "frames": [], "where": "kod"},
            "text": "",
        }
    return {"status": "ok", "text": "\n\n".join(blocks)}


def run(code, stdin=""):
    return execute_code(code)


def test_helpers(code):
    res = execute_code(code)
    if res["status"] == "error":
        err = res["error"]
        raise ADError(err["msg"], line=err.get("line") or 1)

    base_dir = Directory()
    cikti = "".join(t for k, t in res.get("segs", []) if k == "out")
    satirlar = [l for l in cikti.splitlines() if l.strip()]
    sonuclar = [[_object_id(base_dir, o) for o in r["objects"]] for r in res["results"]]
    sonuc = sonuclar[-1] if sonuclar else []
    son_r = res["results"][-1] if res["results"] else {}

    def kullanir(parca):
        temiz = "\n".join(
            l for l in (code or "").splitlines() if not l.strip().startswith("#")
        )
        return parca.casefold() in temiz.casefold()

    def dene(ek=None, guncelle=None, satir_olarak=False):
        raw = load_raw_directory()
        if guncelle:
            for key, degisiklik in guncelle.items():
                k_low = key.casefold()
                for obj in raw:
                    if (
                        str(obj.get("sAMAccountName") or "").casefold() == k_low
                        or str(obj.get("distinguishedName") or "").casefold() == k_low
                        or str(obj.get("name") or "").casefold() == k_low
                    ):
                        obj.update(degisiklik)
        if ek:
            raw.extend(copy.deepcopy(ek))
        r2 = execute_code(code, raw_directory=raw)
        if r2["status"] == "error":
            raise ADError(r2["error"]["msg"], line=r2["error"].get("line") or 1)
        if satir_olarak:
            c2 = "".join(t for k, t in r2.get("segs", []) if k == "out")
            return [l for l in c2.splitlines() if l.strip()]
        d2 = Directory(raw)
        return [_object_id(d2, o) for o in r2["results"][-1]["objects"]] if r2["results"] else []

    def yeni_kullanici(sam, ou="OU=SOC,OU=Merkez", **oz):
        """Sınır testleri için dizine eklenecek sahte bir kullanıcı nesnesi üretir."""
        o = {
            "distinguishedName": f"CN={sam},{ou},{DOMAIN_DN}",
            "sAMAccountName": sam, "cn": sam, "name": sam,
            "objectCategory": "person",
            "objectClass": ["top", "person", "organizationalPerson", "user"],
            "userAccountControl": 512, "adminCount": 0, "badPwdCount": 0,
            "memberOf": [], "servicePrincipalName": [],
        }
        o.update(oz)
        return o

    def yeni_bilgisayar(ad, ou="OU=Istasyonlar", **oz):
        """Sınır testleri için dizine eklenecek sahte bir bilgisayar nesnesi üretir."""
        o = {
            "distinguishedName": f"CN={ad},{ou},{DOMAIN_DN}",
            "sAMAccountName": ad + "$", "cn": ad, "name": ad,
            "objectCategory": "computer",
            "objectClass": ["top", "person", "organizationalPerson", "user", "computer"],
            "userAccountControl": 4096, "adminCount": 0, "badPwdCount": 0,
            "memberOf": [], "servicePrincipalName": [f"HOST/{ad}"],
        }
        o.update(oz)
        return o

    return {
        "src": code,
        "cikti": cikti,
        "satirlar": satirlar,
        "sonuc": sonuc,
        "sonuclar": sonuclar,
        "etkin_ldap": son_r.get("effective_ldap", ""),
        "search_base": son_r.get("search_base", ""),
        "search_scope": son_r.get("search_scope", ""),
        "kullanir": kullanir,
        "dene": dene,
        "yeni_kullanici": yeni_kullanici,
        "yeni_bilgisayar": yeni_bilgisayar,
    }

