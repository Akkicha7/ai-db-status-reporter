from metrics_collector import collect
from analyzer import analyze
from ai_report_generator import generate
from db_config_loader import get_all_db_configs

def run_pipeline():

    print("🚀 Pipeline Start")

    configs = get_all_db_configs()

    if not configs:
        raise Exception("No DB configs found")

    db_config = configs[0]   # ✅ select first DB

    metrics = collect(db_config)   # ✅ FIX HERE

    analysis = analyze(metrics)

    report = generate(analysis)

    print("\n===== FINAL REPORT =====\n")
    print(report)

    return True


if __name__ == "__main__":
    run_pipeline()