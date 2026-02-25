# 速狗海外仓 — 智能报价系统 V2026.06

一站式报价工具，包含：尾程运费报价 · 增值服务计算 · 单位换算 · 操作费明细

## 📁 仓库结构

```
.
├── data/
│   ├── T0.xlsx          ← 客户等级 T0（最优惠）
│   ├── T1.xlsx          ← 客户等级 T1
│   ├── T2.xlsx          ← 客户等级 T2
│   └── T3.xlsx          ← 客户等级 T3（常规）
├── template.html        ← 前端 HTML 模板（含所有 JS 逻辑）
├── build.py             ← 数据提取 + HTML 生成脚本
├── requirements.txt     ← Python 依赖
├── .github/
│   └── workflows/
│       └── build.yml   ← GitHub Actions 自动构建流程
└── public/
    └── index.html       ← ✅ 自动生成，勿手动修改
```

## 🚀 使用方法

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 将报价 Excel 放入 data/ 目录

# 3. 运行构建
python build.py

# 4. 用浏览器打开
open public/index.html
```

### GitHub Pages 自动部署

1. **Fork 或创建此仓库**

2. **开启 GitHub Pages**：
   - 进入仓库 → Settings → Pages
   - Source 选择 **GitHub Actions**

3. **更新报价表**：
   - 将新版 T0/T1/T2/T3.xlsx 替换 `data/` 目录下对应文件
   - Push 到主分支
   - GitHub Actions 自动触发构建 → 约 1~2 分钟后 Pages 更新

4. **手动触发**：
   - 进入 Actions 页面 → "构建报价系统" → "Run workflow"

## 📊 数据读取说明

构建脚本自动从 Excel 读取以下 Sheet：

| Sheet 名 | 说明 |
|---|---|
| `库内操作费` | 出库费、自提费（按重量段） |
| `增值服务费` | 移仓入库、贴换标、包装、退货等 |
| `GOFO-报价` | GOFO 直邮价格 + 邮编数据库 |
| `GOFO、UNIUNI-MT-报价` | GOFO-MT / UniUni-MT 中转价格 |
| `USPS-YSD-报价` | USPS 优速达价格 |
| `FedEx-ECO-MT报价` | FedEx ECO 中转价格 |
| `FedEx-632-MT-报价` | FedEx 标准中转（85折燃油） |
| `FedEx-MT-超大包裹-报价` | FedEx 超大件（85折燃油） |
| `FedEx-MT-危险品-报价` | FedEx 危险品 |
| `GOFO大件-MT-报价` | GOFO 大件中转 |
| `XLmiles-报价` | XLmiles 大件服务 |

## ✨ 功能说明

| 标签页 | 功能 |
|---|---|
| 尾程运费报价 | 输入邮编+规格 → 实时计算所有渠道总价并排序 |
| 增值服务计算 | 按需开启服务开关 → 实时汇总费用明细 |
| 单位换算 | 磅↔千克↔盎司 / 英寸↔厘米↔毫米↔米 动态双向换算 |
| 操作费明细 | 四级客户对照表（出库费 / 自提费） |
