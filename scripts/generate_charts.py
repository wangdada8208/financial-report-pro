#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def f(data, key, default=0.0):
    value = data.get(key)
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def setup_font(plt):
    try:
        import matplotlib.font_manager as fm
    except Exception:
        return
    candidates = ["PingFang SC", "Heiti TC", "Hiragino Sans GB", "Songti SC", "Noto Sans CJK SC", "Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    available = {font.name for font in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name, "sans-serif"]
            plt.rcParams["font.family"] = "sans-serif"
            break
    plt.rcParams["axes.unicode_minus"] = False


def generate(data, ratios, output_dir):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    setup_font(plt)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {}

    palette = ["#1f4e79", "#70ad47", "#ffc000", "#c00000", "#7030a0", "#5b9bd5"]

    labels = ["营业收入", "营业成本", "净利润", "总资产", "总负债", "权益"]
    keys = ["revenue", "cost_of_sales", "net_profit", "total_assets", "total_liabilities", "equity"]
    values = [f(data, key) / 1e8 for key in keys]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, values, color=palette)
    ax.set_ylabel("亿元")
    ax.set_title("核心财务指标")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = output / "financial_overview.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths["financial_overview"] = str(path)

    ratio_labels = ["毛利率", "净利率", "ROE", "净现比", "资产负债率"]
    ratio_keys = ["gross_margin", "net_margin", "roe", "cfo_to_net_profit", "debt_to_asset_ratio"]
    ratio_values = [(ratios.get(key) or 0) * 100 for key in ratio_keys]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(ratio_labels, ratio_values, color=palette[:5])
    ax.set_xlabel("%")
    ax.set_title("盈利与风险指标")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    path = output / "profitability.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths["profitability"] = str(path)

    asset_values = [max(f(data, "cash"), 0), max(f(data, "accounts_receivable"), 0), max(f(data, "inventory"), 0)]
    other_assets = max(f(data, "total_assets") - sum(asset_values), 0)
    asset_values.append(other_assets)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.pie(asset_values, labels=["货币资金", "应收账款", "存货", "其他资产"], autopct=lambda p: f"{p:.1f}%" if p > 0 else "", colors=palette[:4])
    ax.set_title("资产结构")
    fig.tight_layout()
    path = output / "asset_structure.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths["asset_structure"] = str(path)

    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--ratios", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    ratios = json.loads(Path(args.ratios).read_text(encoding="utf-8"))
    result = generate(data, ratios, args.output_dir)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
