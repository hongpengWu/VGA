import re
from collections import defaultdict
from pathlib import Path
import json


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def extract_aff_from_comma_line(line: str) -> str | None:
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 3:
        return None
    return ",".join(parts[2:]).strip()


def extract_aff_from_presenter_line(line: str) -> str | None:
    if ":" in line:
        line = line.split(":", 1)[1].strip()
    parts = [p.strip() for p in line.split(",")]
    if len(parts) >= 3:
        return ",".join(parts[2:]).strip()
    if len(parts) == 2:
        return parts[1]
    return None


def looks_like_aff(line: str) -> bool:
    l = line.strip()
    if not l:
        return False
    if l.endswith(":"):
        return False
    if l.startswith(("Paper ", "Poster ", "Title:", "Abstract:", "Bio.:")):
        return False
    kw = (
        "University",
        "Institute",
        "Academy",
        "College",
        "Laboratory",
        "Lab",
        "Center",
        "Centre",
        "Inc",
        "Ltd",
        "Co.",
        "Corporation",
        "GmbH",
        "A*STAR",
        "Synopsys",
        "Cadence",
        "Siemens",
        "Applied Materials",
        "GlobalFoundries",
        "AWS",
        "Technology",
        "Technologies",
    )
    return any(k in l for k in kw)


def extract_aff_from_name_aff_line(line: str) -> str | None:
    s = line.strip().lstrip("-").strip()
    if not s:
        return None
    if "Bio.:" in s or s.startswith(("Bio.:", "Abstract:", "Title:")):
        return None
    if "," not in s:
        return None
    parts = [p.strip() for p in s.split(",")]
    if len(parts) < 3:
        return None
    first = parts[0]
    if not (
        first.startswith(("Prof.", "Dr.", "Mr.", "Ms."))
        or re.match(r"^[A-Z][A-Za-z\-'. ]+$", first)
    ):
        return None
    aff = ",".join(parts[2:]).strip()
    if not aff or not looks_like_aff(aff):
        return None
    return aff


def map_aff_to_unit(aff: str) -> str | None:
    a = aff.lower()
    rules = [
        (r"institute of computing technology", "中国科学院计算技术研究所"),
        (r"university of chinese academy of sciences", "中国科学院大学"),
        (r"academy of mathematics and systems science", "中国科学院数学与系统科学研究院"),
        (r"institute of software, chinese academy of sciences", "中国科学院软件研究所"),
        (r"institute of microelectronics, chinese academy of sciences", "中国科学院微电子研究所"),
        (r"peng cheng laboratory", "深圳市鹏城实验室"),
        (r"national integrated circuit design automation technology innovation center", "国家EDA技术创新中心"),
        (r"p e k i n g university|peking university", "北京大学"),
        (r"southeast university", "东南大学"),
        (r"fudan university", "复旦大学"),
        (r"shanghai jiao tong university", "上海交通大学"),
        (r"beihang university", "北京航空航天大学"),
        (r"xidian university", "西安电子科技大学"),
        (r"zhejiang university", "浙江大学"),
        (r"southern university of science and technology", "南方科技大学"),
        (r"ningbo university", "宁波大学"),
        (r"nanjing university of aeronautics", "南京航空航天大学"),
        (r"nanjing university of science and technology", "南京理工大学"),
        (r"nanjing university", "南京大学"),
        (r"hangzhou dianzi university", "杭州电子科技大学"),
        (r"east china normal university", "华东师范大学"),
        (r"university of science and technology of china", "中国科学技术大学"),
        (r"huazhong university of science and technology", "华中科技大学"),
        (r"university of science and technology beijing", "北京科技大学"),
        (r"south china university of technology", "华南理工大学"),
        (r"shanghai tech university", "上海科技大学"),
        (r"fuzhou university", "福州大学"),
        (r"jimei university", "集美大学"),
        (r"guangdong university of technology", "广东工业大学"),
        (r"jiangnan university", "江南大学"),
        (r"sun yat-sen university", "中山大学"),
        (r"university of electronic science and technology of china", "电子科技大学"),
        (r"tsinghua university", "清华大学"),
        (r"the chinese university of hong kong", "香港中文大学"),
        (r"the hong kong university of science and technology \\(guangzhou\\)", "香港科技大学（广州）"),
        (r"the hong kong university of science and technology", "香港科技大学"),
        (r"the hong kong polytechnic university", "香港理工大学"),
        (r"ime singapore", "新加坡科技研究局微电子研究院（IME Singapore）"),
        (r"nanyang technological university", "新加坡南洋理工大学"),
        (r"singapore university of technology and design", "新加坡科技设计大学"),
        (r"national university of singapore", "新加坡国立大学"),
        (r"technical university of munich|university of munich \\(tum\\)", "慕尼黑工业大学"),
        (r"ku leuven|katholieke universiteit leuven", "鲁汶大学"),
        (r"university of southampton", "南安普顿大学"),
        (r"university of california, los angeles", "加州大学洛杉矶分校"),
        (r"university of california, davis", "加州大学戴维斯分校"),
        (r"arizona state university", "亚利桑那州立大学"),
        (r"university of stuttgart", "斯图加特大学"),
        (r"university of maryland", "马里兰大学"),
        (r"university of minnesota", "明尼苏达大学（明尼阿波利斯/双城校区）"),
        (r"tokyo.*science", "东京科学大学"),
        (r"mcmaster university", "麦克马斯特大学"),
        (r"pennsylvania state university", "宾夕法尼亚州立大学"),
        (r"rensselaer polytechnic institute", "伦斯勒理工学院"),
        (r"university of florida", "佛罗里达大学"),
        (r"university of alberta", "阿尔伯塔大学"),
        (r"technical university of darmstadt", "达姆施塔特工业大学"),
        (r"sapienza university of rome", "罗马第一大学（萨皮恩扎大学）"),
        (r"singapore institute of technology", "新加坡理工大学"),
        (r"indian institute of technology delhi", "印度理工学院德里分校"),
        (r"a\\*star", "新加坡科技研究局 (A*STAR)"),
        (r"applied materials", "应用材料公司 (Applied Materials)"),
        (r"synopsys", "新思科技 (Synopsys)"),
        (r"globalfoundries", "格芯 (GlobalFoundries)"),
        (r"cadence", "Cadence Design Systems, Inc."),
        (r"siemens eda", "西门子EDA(Siemens EDA)"),
        (r"aws", "AWS"),
        (r"ennocad", "Ennocad Electronics Technology Company, Ltd."),
        (r"sanechips", "Sanechips Technology Co., Ltd."),
        (r"semitronix", "Semitronix Corporation"),
        (r"shenzhen funxin technology corporation", "深圳泛信科技有限公司"),
        (r"changxin memory technologies", "长鑫存储"),
        (r"shanghai pftn semiconductor", "上海PFTN半导体有限公司"),
        (r"huaxin jushu", "华芯巨数（杭州）微电子有限公司"),
        (r"huada empyrean", "华大九天（Huada Empyrean）"),
        (r"sichip", "珠海硅芯科技有限公司（SiChip Technology）"),
        (r"ikas industries", "IKAS INDUSTRIES"),
    ]
    for pat, unit in rules:
        if re.search(pat, a):
            return unit
    return None


def count_roles(md_lines: list[str]) -> dict[str, dict[str, int]]:
    role_aff = {
        "keynote": defaultdict(int),
        "tutorial": defaultdict(int),
        "session_chair": defaultdict(int),
        "committee": defaultdict(int),
        "panel": defaultdict(int),
        "invited": defaultdict(int),
    }

    # Keynote: Speech Title blocks
    for i, ln in enumerate(md_lines):
        if "Speech Title:" not in ln:
            continue
        aff = None
        for j in range(i - 1, max(-1, i - 8), -1):
            prev = md_lines[j].strip()
            if not prev:
                continue
            if looks_like_aff(prev):
                aff = prev
                break
        if aff:
            role_aff["keynote"][norm_space(aff)] += 1

    # Session chair
    for ln in md_lines:
        if ln.strip().startswith("Session Chair:"):
            aff = extract_aff_from_presenter_line(ln.replace("Session Chair:", "Presenter:", 1))
            if aff:
                role_aff["session_chair"][norm_space(aff)] += 1

    # Invited talk (subset of oral): Paper ID line contains Invited Talk + subsequent Presenter
    cur_invited = False
    invited_pending_aff = False
    for ln in md_lines:
        if "Paper ID:" in ln:
            cur_invited = "Invited Talk" in ln
            invited_pending_aff = False
        if cur_invited and ln.strip().startswith("Presenter:"):
            aff = extract_aff_from_presenter_line(ln)
            if aff:
                role_aff["invited"][norm_space(aff)] += 1
                cur_invited = False
            continue
        if cur_invited and "Invited Talk" in ln:
            invited_pending_aff = True
            continue
        if invited_pending_aff and looks_like_aff(ln):
            role_aff["invited"][norm_space(ln)] += 1
            invited_pending_aff = False
            cur_invited = False

    # Tutorial roles: within tutorial blocks
    inside_tutorial = False
    for ln in md_lines:
        l = ln.strip()
        if l.startswith("Tutorial"):
            inside_tutorial = True
            continue
        if inside_tutorial and l.startswith(("TECHNICAL SESSIONS", "PANELS", "Workshops", "WORKSHOP", "WORKSHOPS")):
            inside_tutorial = False
        if not inside_tutorial:
            continue
        aff = extract_aff_from_name_aff_line(ln)
        if aff:
            role_aff["tutorial"][norm_space(aff)] += 1

    # Committee/Chair roles: headings ending with Chair/Chairs or containing Committee (excluding Session Chair)
    in_committee_section = False
    blank_run = 0
    for ln in md_lines:
        l = ln.strip()
        if l.startswith("Session Chair:"):
            in_committee_section = False
            blank_run = 0
            continue
        if (l.endswith("Chair") or l.endswith("Chairs") or "Committee" in l or l.endswith("Co-Chair")) and not l.startswith("Session Chair"):
            in_committee_section = True
            blank_run = 0
            continue
        if in_committee_section:
            if not l:
                blank_run += 1
                if blank_run >= 3:
                    in_committee_section = False
                continue
            blank_run = 0
            aff = extract_aff_from_name_aff_line(ln)
            if aff:
                role_aff["committee"][norm_space(aff)] += 1
            if l.startswith(("Track", "Special", "Tutorial", "Workshops", "WORKSHOP", "WORKSHOPS", "PANELS", "TECHNICAL")):
                in_committee_section = False

    # Panels: Moderator / Panelists / Panel Chair blocks
    panel_ctx = False
    for ln in md_lines:
        l = ln.strip()
        if l in ("Panelists", "Panelist", "Panel Chair", "Panel Chair-US", "Panel Chair-Europe", "Moderator") or l.startswith(
            ("Panelists", "Panel Chair")
        ):
            panel_ctx = True
            continue
        if panel_ctx:
            if not l or l.endswith(":") or l.startswith(("Special Sessions", "Tutorial", "TECHNICAL", "Workshops", "WORKSHOP", "WORKSHOPS")):
                panel_ctx = False
                continue
            aff = extract_aff_from_name_aff_line(ln)
            if aff:
                role_aff["panel"][norm_space(aff)] += 1

    role_unit = {k: defaultdict(int) for k in role_aff.keys()}
    unmapped = {k: defaultdict(int) for k in role_aff.keys()}
    for role, aff_map in role_aff.items():
        for aff, c in aff_map.items():
            unit = map_aff_to_unit(aff)
            if unit:
                role_unit[role][unit] += c
            else:
                unmapped[role][aff] += c

    return {
        "mapped": {k: dict(v) for k, v in role_unit.items()},
        "unmapped_top": {
            k: dict(sorted(v.items(), key=lambda x: (-x[1], x[0]))[:50]) for k, v in unmapped.items()
        },
    }


def generate_updated_tex(tex_text: str, role_counts: dict[str, dict[str, int]]) -> str:
    # Update 3 tables: replace 5-column header with expanded header, and expand each row.
    # Existing rows format:
    # 单位 & Oral & Poster & 其他 & 总计 \\
    # New rows:
    # 单位 & Oral & Poster & Keynote & Tutorial & SessionChair & Committee & Panel & Total \\

    def repl_table(match: re.Match) -> str:
        table_body = match.group(0)
        lines = table_body.splitlines(True)
        out_lines = []
        for ln in lines:
            if ln.strip().startswith("\\begin{longtable}"):
                out_lines.append("\\small\n\\setlength{\\tabcolsep}{2pt}\n\\renewcommand{\\arraystretch}{1.15}\n")
                out_lines.append(
                    ln.replace(
                        "{|p{8cm}|c|c|c|c|}",
                        "{|p{5.2cm}|c|c|c|c|c|c|c|c|c|c|}",
                    )
                )
                continue
            if "textbf{单位名称}" in ln and "Oral" in ln and "Poster" in ln:
                out_lines.append(
                    "\\textbf{单位名称} & \\textbf{Oral} & \\textbf{Poster} & \\textbf{Keynote} & \\textbf{Invited} & \\textbf{Tutorial} & \\textbf{Sess. Chair} & \\textbf{Committee} & \\textbf{Panel} & \\textbf{Other} & \\textbf{总计} \\\\\n"
                )
                continue

            m = re.match(
                r"^(?P<unit>[^&]+?)\s*&\s*(?P<oral>\d+)\s*&\s*(?P<poster>\d+)\s*&\s*(?P<other>\d+)\s*&\s*(?P<total>\d+)\s*\\\\",
                ln,
            )
            if m:
                unit = m.group("unit").strip()
                oral = int(m.group("oral"))
                poster = int(m.group("poster"))
                other_old = int(m.group("other"))
                keynote = int(role_counts.get("keynote", {}).get(unit, 0))
                invited = int(role_counts.get("invited", {}).get(unit, 0))
                tutorial = int(role_counts.get("tutorial", {}).get(unit, 0))
                session_chair = int(role_counts.get("session_chair", {}).get(unit, 0))
                committee = int(role_counts.get("committee", {}).get(unit, 0))
                panel = int(role_counts.get("panel", {}).get(unit, 0))
                known_other = keynote + tutorial + session_chair + committee + panel
                other_residual = other_old - known_other
                if other_residual < 0:
                    other_residual = 0
                total = oral + poster + known_other + other_residual
                out_lines.append(
                    f"{unit} & {oral} & {poster} & {keynote} & {invited} & {tutorial} & {session_chair} & {committee} & {panel} & {other_residual} & {total} \\\\\n"
                )
                continue
            out_lines.append(ln)
        return "".join(out_lines)

    # Match each longtable block
    pattern = re.compile(r"\\begin\{longtable\}.*?\\end\{longtable\}", re.S)
    updated = pattern.sub(repl_table, tex_text)
    return updated


def main() -> None:
    root = Path(r"e:\\SHT\\VGA")
    md_path = root / "huizong.md"
    tex_path = root / "huizong_new.tex"
    out_tex_path = root / "_huizong_new_generated.tex"
    out_json_path = root / "_huizong_role_counts.json"

    md_lines = md_path.read_text(encoding="utf-8").splitlines()
    role_data = count_roles(md_lines)
    out_json_path.write_text(json.dumps(role_data, ensure_ascii=False, indent=2), encoding="utf-8")

    role_counts = role_data["mapped"]
    tex_text = tex_path.read_text(encoding="utf-8")
    out_tex_path.write_text(generate_updated_tex(tex_text, role_counts), encoding="utf-8")


if __name__ == "__main__":
    main()
