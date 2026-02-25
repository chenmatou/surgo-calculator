#!/usr/bin/env python3
"""
速狗海外仓 综合报价系统 - 构建脚本 V2026.06
自动读取 data/T*.xlsx，提取运费、操作费、增值服务费，
注入 HTML 模板，生成 public/index.html。

仓库文件更新后由 GitHub Actions 自动触发本脚本。
"""

import pandas as pd
import json
import re
import os
import warnings
import decimal
from pathlib import Path

warnings.filterwarnings('ignore', category=UserWarning)

# ────────────────────────────────────────────────
# 全局路径
# ────────────────────────────────────────────────
DATA_DIR   = Path("data")
OUTPUT_DIR = Path("public")

TIER_FILES = {"T0": "T0.xlsx", "T1": "T1.xlsx", "T2": "T2.xlsx", "T3": "T3.xlsx"}

# ────────────────────────────────────────────────
# 仓库数据库
# ────────────────────────────────────────────────
WAREHOUSE_DB = {
    "60632": {"name": "SureGo美中芝加哥-60632仓",      "region": "CENTRAL"},
    "91730": {"name": "SureGo美西库卡蒙格-91730仓",    "region": "WEST"},
    "91752": {"name": "SureGo美西米拉罗马-91752仓",    "region": "WEST"},
    "08691": {"name": "SureGo美东新泽西-08691仓",      "region": "EAST"},
    "06801": {"name": "SureGo美东贝塞尔-06801仓",      "region": "EAST"},
    "11791": {"name": "SureGo美东长岛-11791仓",        "region": "EAST"},
    "07032": {"name": "SureGo美东新泽西-07032仓",      "region": "EAST"},
    "63461": {"name": "SureGo退货检测-密苏里63461仓",  "region": "CENTRAL"},
}

US_STATES_CN = {
    'AL':'阿拉巴马','AK':'阿拉斯加','AZ':'亚利桑那','AR':'阿肯色','CA':'加利福尼亚',
    'CO':'科罗拉多','CT':'康涅狄格','DE':'特拉华','FL':'佛罗里达','GA':'佐治亚',
    'HI':'夏威夷','ID':'爱达荷','IL':'伊利诺伊','IN':'印第安纳','IA':'爱荷华',
    'KS':'堪萨斯','KY':'肯塔基','LA':'路易斯安那','ME':'缅因','MD':'马里兰',
    'MA':'马萨诸塞','MI':'密歇根','MN':'明尼苏达','MS':'密西西比','MO':'密苏里',
    'MT':'蒙大拿','NE':'内布拉斯加','NV':'内华达','NH':'新罕布什尔','NJ':'新泽西',
    'NM':'新墨西哥','NY':'纽约','NC':'北卡罗来纳','ND':'北达科他','OH':'俄亥俄',
    'OK':'俄克拉荷马','OR':'俄勒冈','PA':'宾夕法尼亚','RI':'罗德岛','SC':'南卡罗来纳',
    'SD':'南达科他','TN':'田纳西','TX':'德克萨斯','UT':'犹他','VT':'佛蒙特',
    'VA':'弗吉尼亚','WA':'华盛顿','WV':'西弗吉尼亚','WI':'威斯康星','WY':'怀俄明',
    'DC':'华盛顿特区'
}

# ────────────────────────────────────────────────
# 渠道配置
# ────────────────────────────────────────────────
CHANNEL_CONFIG = {
    "GOFO-报价":               {"sheet_name":"GOFO-报价",              "fuel_mode":"none",       "zone_source":"gofo",   "dim_divisor":250,"meta_loc":(1,0),"sig_location":None},
    "GOFO-MT-报价":             {"sheet_name":"GOFO、UNIUNI-MT-报价",   "sheet_side":"left",      "fuel_mode":"included", "zone_source":"gofo",   "dim_divisor":250,"meta_loc":(1,0),"sig_location":None},
    "UNIUNI-MT-报价":           {"sheet_name":"GOFO、UNIUNI-MT-报价",   "sheet_side":"right",     "fuel_mode":"none",     "zone_source":"general","dim_divisor":250,"meta_loc":(1,0),"sig_location":None},
    "USPS-YSD-报价":            {"sheet_name":"USPS-YSD-报价",          "fuel_mode":"none",       "zone_source":"general","dim_divisor":250,"no_peak":True,"meta_loc":(2,0),"sig_location":None},
    "FedEx-632-MT-报价":        {"sheet_name":"FedEx-632-MT-报价",      "fuel_mode":"discount_85","zone_source":"general","dim_divisor":250,"surcharges":"fedex_new","meta_loc":(1,0),"res_fee_loc":(179,6),"sig_location":{"direct":[177,16],"adult":[178,16]}},
    "FedEx-MT-超大包裹-报价":   {"sheet_name":"FedEx-MT-超大包裹-报价", "fuel_mode":"discount_85","zone_source":"general","dim_divisor":250,"surcharges":"fedex_new","meta_loc":(1,0),"res_fee_loc":(90,6),"sig_location":{"direct":[88,16],"adult":[89,16]}},
    "FedEx-ECO-MT报价":         {"sheet_name":"FedEx-ECO-MT报价",       "fuel_mode":"included",   "zone_source":"general","dim_divisor":250,"surcharges":"fedex_new","meta_loc":(1,0),"sig_location":None},
    "FedEx-MT-危险品-报价":     {"sheet_name":"FedEx-MT-危险品-报价",   "fuel_mode":"standard",   "zone_source":"general","dim_divisor":250,"surcharges":"fedex_new","meta_loc":(1,0),"res_fee_loc":(179,6),"sig_location":{"direct":[177,16],"adult":[178,16]}},
    "GOFO大件-MT-报价":         {"sheet_name":"GOFO大件-MT-报价",       "fuel_mode":"standard",   "zone_source":"gofo",   "dim_divisor":250,"meta_loc":(1,0),"res_fee_loc":(179,6),"sig_location":None},
    "XLmiles-报价":             {"sheet_name":"XLmiles-报价",           "fuel_mode":"none",       "zone_source":"xlmiles","dim_divisor":250,"meta_loc":None,"sig_location":{"direct":[14,3],"adult":None}},
}

# ────────────────────────────────────────────────
# 工具函数
# ────────────────────────────────────────────────
def clean_num(val):
    if pd.isna(val) or str(val).strip() == "": return 0.0
    s = str(val).replace('$','').replace(',','').strip()
    try:
        d = decimal.Decimal(s)
        return float(d.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP))
    except: return 0.0

def safe_float(v, default=0.0):
    try: return float(str(v).replace(',','').strip())
    except: return default

def find_sheet(xl, target):
    for s in xl.sheet_names:
        if s == target: return s
    for s in xl.sheet_names:
        if target in s: return s
    return None

def parse_allowed_wh(text):
    if not isinstance(text, str):
        return list(WAREHOUSE_DB.keys())
    allowed = []
    if "美西" in text: allowed.extend(["91730","91752"])
    if "美中" in text: allowed.extend(["60632"])
    if "美东" in text: allowed.extend(["08691","06801","11791","07032"])
    return allowed if allowed else list(WAREHOUSE_DB.keys())

# ────────────────────────────────────────────────
# 提取 GOFO ZIP 数据库
# ────────────────────────────────────────────────
def load_gofo_zips(tier_file):
    db = {}
    path = DATA_DIR / tier_file
    if not path.exists(): return db
    try:
        xl = pd.ExcelFile(path)
        sheet = find_sheet(xl, "GOFO-报价")
        if not sheet: return db
        df = pd.read_excel(xl, sheet_name=sheet, header=None)
        cols = {}
        start_row = -1
        for r in range(df.shape[0]-1, max(-1, df.shape[0]-600), -1):
            rv = [str(x).strip() for x in df.iloc[r].values]
            if any("邮编" in x for x in rv):
                start_row = r
                for c, v in enumerate(rv):
                    if "邮编" in v: cols['zip'] = c
                    elif "城市" in v: cols['city'] = c
                    elif "省州" in v: cols['state'] = c
                    elif "大区" in v: cols['region'] = c
                break
        if start_row != -1 and 'zip' in cols:
            for r in range(start_row+1, len(df)):
                try:
                    raw = str(df.iloc[r, cols['zip']]).split('.')[0].strip().zfill(5)
                    if len(raw)==5 and raw.isdigit():
                        st = str(df.iloc[r, cols.get('state',-1)]).strip().upper()
                        db[raw] = {
                            "city":   str(df.iloc[r, cols.get('city',-1)]).strip(),
                            "state":  st,
                            "cn_state": US_STATES_CN.get(st, st),
                            "region": str(df.iloc[r, cols.get('region',-1)]).strip()
                        }
                except: pass
    except Exception as e:
        print(f"  GOFO ZIP 提取警告: {e}")
    return db

# ────────────────────────────────────────────────
# 提取运费价格表
# ────────────────────────────────────────────────
def extract_shipping_prices(df, conf, channel_name):
    if df is None: return [], list(WAREHOUSE_DB.keys()), 0.0, 0.0, 0.0

    allowed_wh = list(WAREHOUSE_DB.keys())
    if conf.get("meta_loc"):
        mr, mc = conf["meta_loc"]
        if df.shape[0] > mr and df.shape[1] > mc:
            allowed_wh = parse_allowed_wh(str(df.iloc[mr, mc]))

    res_fee = 0.0
    if conf.get("res_fee_loc"):
        rr, rc = conf["res_fee_loc"]
        if df.shape[0] > rr and df.shape[1] > rc:
            res_fee = clean_num(df.iloc[rr, rc])

    sig_direct = sig_adult = 0.0
    if conf.get("sig_location"):
        loc = conf["sig_location"]
        if loc.get("direct"):
            dr, dc = loc["direct"]
            if df.shape[0] > dr and df.shape[1] > dc: sig_direct = clean_num(df.iloc[dr, dc])
        if loc.get("adult"):
            ar, ac = loc["adult"]
            if df.shape[0] > ar and df.shape[1] > ac: sig_adult = clean_num(df.iloc[ar, ac])

    total_cols = df.shape[1]
    c_start, c_end = 0, total_cols
    split_side = conf.get("sheet_side")

    if split_side:
        weight_indices = []
        for c in range(total_cols):
            for r in range(50):
                val = str(df.iloc[r, c]).lower()
                if ('weight' in val or '重量' in val or '磅' in val or 'lb' in val) and 'kg' not in val:
                    if c not in weight_indices: weight_indices.append(c)
                    break
        weight_indices.sort()
        if split_side == 'left' and len(weight_indices) > 1: c_end = weight_indices[1]
        elif split_side == 'right':
            if len(weight_indices) > 1: c_start = weight_indices[1]
            else: return [], allowed_wh, res_fee, sig_direct, sig_adult

    # XLmiles special parse
    if "XLmiles" in channel_name:
        prices = []
        h_row, z_map = -1, {}
        for r in range(20):
            rv = [str(x).lower() for x in df.iloc[r].values]
            if any("zone" in x for x in rv):
                h_row = r
                for c, v in enumerate(rv):
                    m = re.search(r'zone\D*(\d+)', v)
                    if m: z_map[int(m.group(1))] = c
                break
        if h_row == -1 or not z_map: return [], allowed_wh, res_fee, sig_direct, sig_adult
        cur_svc = "AH"
        for r in range(h_row+1, len(df)):
            try:
                sv = str(df.iloc[r, 0])
                if "AH" in sv: cur_svc="AH"
                elif "OS" in sv: cur_svc="OS"
                elif "OM" in sv: cur_svc="OM"
                nums = re.findall(r'\d+', str(df.iloc[r, 2]))
                if not nums: continue
                w = float(nums[-1])
                ent = {'service': cur_svc, 'w': w}
                for z, c in z_map.items():
                    p = clean_num(df.iloc[r, c])
                    if p > 0: ent[z] = p
                prices.append(ent)
            except: pass
        return prices, allowed_wh, res_fee, sig_direct, sig_adult

    # General parse
    h_row = -1
    for r in range(200):
        rv = [str(x).lower() for x in df.iloc[r, c_start:c_end].values]
        has_w = any(('weight' in x or '重量' in x or 'lb' in x or '磅' in x) and 'kg' not in x for x in rv)
        has_z = any('zone' in x for x in rv)
        if has_w and has_z: h_row = r; break
    if h_row == -1: return [], allowed_wh, res_fee, sig_direct, sig_adult

    row_dat = df.iloc[h_row]
    w_col, z_map = -1, {}
    for c in range(c_start, min(c_end, total_cols)):
        v = str(row_dat[c]).strip().lower()
        if ('weight' in v or '重量' in v or 'lb' in v or '磅' in v) and 'kg' not in v and w_col == -1:
            w_col = c
        m = re.search(r'zone[\D]*(\d+)', v)
        if m: z_map[int(m.group(1))] = c

    if w_col == -1 or not z_map: return [], allowed_wh, res_fee, sig_direct, sig_adult

    prices = []
    for r in range(h_row+1, len(df)):
        try:
            w_str = str(df.iloc[r, w_col]).lower().strip()
            nums = re.findall(r'[\d\.]+', w_str)
            if not nums: continue
            w = float(nums[0])
            if 'oz' in w_str: w /= 16.0
            if w <= 0: continue
            ent = {'w': w}
            valid = False
            for z, c in z_map.items():
                p = clean_num(df.iloc[r, c])
                if p > 0: ent[z] = p; valid = True
            if valid: prices.append(ent)
        except: pass

    prices.sort(key=lambda x: x['w'])
    return prices, allowed_wh, res_fee, sig_direct, sig_adult

# ────────────────────────────────────────────────
# 提取库内操作费
# ────────────────────────────────────────────────
def extract_op_fees(xl):
    sheet = find_sheet(xl, "库内操作费")
    if not sheet: return {}, {}
    df = pd.read_excel(xl, sheet_name=sheet, header=None)

    outbound, pickup = {}, {}

    def _parse_rows(start, end, target_dict):
        for i in range(start, min(end, len(df))):
            r = df.iloc[i]
            rng = str(r[1]) if str(r[1]) != 'nan' else ''
            price_str = str(r[3])
            if rng and price_str not in ('nan', '免费', ''):
                try: target_dict[rng] = float(price_str)
                except: pass
            elif rng and price_str in ('免费',):
                target_dict[rng] = 0.0

    _parse_rows(17, 35, outbound)
    _parse_rows(35, 53, pickup)
    return outbound, pickup

# ────────────────────────────────────────────────
# 提取增值服务费
# ────────────────────────────────────────────────
def extract_vas(xl):
    sheet = find_sheet(xl, "增值服务费")
    if not sheet: return {}
    df = pd.read_excel(xl, sheet_name=sheet, header=None)
    n = len(df)

    def row(i, c=3):
        if i < n and c < df.shape[1]: return df.iloc[i, c]
        return None

    def sfv(i, c=3): return safe_float(row(i,c), 0.0)

    # 贴箱唛价格 row 52 col3 可能是 "$0.5/张" 或 0.5
    box_label_raw = row(52, 3)
    box_label = 0.5
    if box_label_raw:
        m = re.search(r'[\d\.]+', str(box_label_raw))
        if m: box_label = float(m.group())

    vas = {
        "return_inbound":    sfv(4),
        "photo":             sfv(5),
        "attach_packing_list": sfv(8),
        "disposal_per_lb":   0.25,
        "pallet_fee":        sfv(20),
        "box_label":         box_label,
        "packing": {
            "bag_s":  sfv(12), "bag_m":  sfv(13), "bag_l":  sfv(14),
            "bubble": sfv(15),
            "box_s":  sfv(16), "box_m":  sfv(17), "box_l":  sfv(18),
        },
        "inventory_check": [
            {"range":"0~9.9LB",   "price": sfv(22)},
            {"range":"10~19.9LB", "price": sfv(23)},
            {"range":"20~29.9LB", "price": sfv(24)},
            {"range":"30~49.9LB", "price": sfv(25)},
            {"range":">50LB",     "price": sfv(26)},
        ],
        "amazon_inbound": {
            "1sku": [
                {"wt":"0-9.9LB",   "price": sfv(30)},
                {"wt":"10-29.9LB", "price": sfv(31)},
                {"wt":"30LB+",     "price": sfv(32)},
            ],
            "2-5sku": [
                {"wt":"0-9.9LB",   "price": sfv(33)},
                {"wt":"10-29.9LB", "price": sfv(34)},
                {"wt":"30LB+",     "price": sfv(35)},
            ],
            "6+sku": [
                {"wt":"0-9.9LB",   "price": sfv(36)},
                {"wt":"10-29.9LB", "price": sfv(37)},
                {"wt":"30LB+",     "price": sfv(38)},
            ],
        },
        # 换标费: rows 43-51, cols 3-6 → <100 / 100-199 / 200-500 / 500+
        "labeling": {
            "1sku": {
                "tiers": [
                    {"range":"<100个",    "price": sfv(43,3)},
                    {"range":"100~199个", "price": sfv(43,4)},
                    {"range":"200~500个", "price": sfv(43,5)},
                    {"range":"500+个",    "price": sfv(43,6)},
                ]
            },
            "2-5sku": {
                "tiers": [
                    {"range":"<100个",    "price": sfv(46,3)},
                    {"range":"100~199个", "price": sfv(46,4)},
                    {"range":"200~500个", "price": sfv(46,5)},
                    {"range":"500+个",    "price": sfv(46,6)},
                ]
            },
            "6+sku": {
                "tiers": [
                    {"range":"<100个",    "price": sfv(49,3)},
                    {"range":"100~199个", "price": sfv(49,4)},
                    {"range":"200~500个", "price": sfv(49,5)},
                    {"range":"500+个",    "price": sfv(49,6)},
                ]
            },
        },
        # 加急工单 rows 75-78
        "urgent_order": [
            {"time":"<5分钟",   "price": sfv(75,4)},
            {"time":"5~30分钟", "price": sfv(76,4)},
            {"time":"30~60分钟","price": sfv(77,4)},
            {"time":">1小时",   "price": sfv(78,4)},
        ],
    }
    return vas

# ────────────────────────────────────────────────
# 提取燃油率
# ────────────────────────────────────────────────
def extract_fuel_rate(xl):
    for sheet in xl.sheet_names:
        if "MT" in sheet.upper() or "632" in sheet:
            try:
                df = pd.read_excel(xl, sheet_name=sheet, header=None)
                for r in range(min(50, df.shape[0])):
                    for c in range(min(50, df.shape[1])):
                        if "燃油" in str(df.iloc[r, c]) and c+1 < df.shape[1]:
                            v = str(df.iloc[r, c+1]).replace('%','').strip()
                            try:
                                f = float(v)
                                if f > 1: f /= 100.0
                                if 0 < f < 1: return f
                            except: pass
            except: pass
    return 0.16

# ────────────────────────────────────────────────
# 主构建逻辑
# ────────────────────────────────────────────────
def build():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("速狗海外仓报价系统 — 构建脚本 V2026.06")
    print("=" * 60)

    gofo_zips = load_gofo_zips(TIER_FILES["T0"])
    print(f"GOFO ZIP 数据库: {len(gofo_zips)} 条")

    all_data = {
        "warehouses":    WAREHOUSE_DB,
        "channels":      CHANNEL_CONFIG,
        "gofo_zips":     gofo_zips,
        "us_states_cn":  US_STATES_CN,
        "tiers":         {}
    }

    for tier, fname in TIER_FILES.items():
        path = DATA_DIR / fname
        print(f"\n处理 {tier} ({fname})...")
        if not path.exists():
            print("  [跳过] 文件不存在"); continue
        try:
            xl = pd.ExcelFile(path)
            fuel_rate = extract_fuel_rate(xl)
            outbound, pickup = extract_op_fees(xl)
            vas = extract_vas(xl)
            print(f"  燃油率: {fuel_rate*100:.2f}%  |  出库费档次: {len(outbound)}  |  增值服务项: {len(vas)}")

            tier_data = {
                "fuel_rate": fuel_rate,
                "outbound":  outbound,
                "pickup":    pickup,
                "vas":       vas,
                "channels":  {}
            }

            for ch_key, conf in CHANNEL_CONFIG.items():
                try:
                    sheet = find_sheet(xl, conf["sheet_name"])
                    if not sheet: continue
                    df = pd.read_excel(xl, sheet_name=sheet, header=None)
                    prices, allow_wh, res_fee, sig_direct, sig_adult = extract_shipping_prices(df, conf, ch_key)
                    if prices:
                        tier_data["channels"][ch_key] = {
                            "prices":    prices,
                            "allow_wh":  allow_wh,
                            "res_fee":   res_fee,
                            "sig_direct":sig_direct,
                            "sig_adult": sig_adult,
                        }
                        print(f"  ✅ {ch_key}: {len(prices)}档 仓:{len(allow_wh)} 住宅:${res_fee:.2f} 签:${sig_direct:.2f}/${sig_adult:.2f}")
                    else:
                        print(f"  ⚠  {ch_key}: 未能提取价格档次")
                except Exception as e:
                    print(f"  ⚠  {ch_key}: 跳过 ({str(e)[:50]})")

            all_data["tiers"][tier] = tier_data
        except Exception as e:
            print(f"  ❌ 错误: {e}")

    # 注入 HTML
    template_path = Path(__file__).parent / "template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    json_str = json.dumps(all_data, ensure_ascii=False).replace("NaN", "0")
    html = html.replace("__BUILD_DATA__", json_str)

    out = OUTPUT_DIR / "index.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    size = out.stat().st_size / 1024
    print(f"\n{'='*60}")
    print(f"✅ 生成成功: {out}  ({size:.1f} KB)")
    print(f"   Tier 数量: {len(all_data['tiers'])}  |  GOFO邮编: {len(gofo_zips)}")

if __name__ == "__main__":
    build()
