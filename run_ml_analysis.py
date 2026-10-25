"""Train/evaluate a Random Forest demand model and predict rows in test.csv.
Run from the project root: python run_ml_analysis.py
"""
from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

TRAIN_PATH = DATA / "train.csv"
TEST_PATH = DATA / "test.csv"
if not TRAIN_PATH.exists() or not TEST_PATH.exists():
    raise FileNotFoundError("لم أجد data/raw/train.csv أو data/raw/test.csv. تحقق من مسار المشروع.")

train = pd.read_csv(TRAIN_PATH)
test = pd.read_csv(TEST_PATH)

FEATURES = ["week", "center_id", "meal_id", "checkout_price", "base_price",
            "emailer_for_promotion", "homepage_featured", "discount_pct", "price_gap"]

def prepare_features(df):
    out = df.copy()
    base = out["base_price"].replace(0, np.nan)
    out["discount_pct"] = ((out["base_price"] - out["checkout_price"]) / base).fillna(0).clip(-5, 1)
    out["price_gap"] = out["base_price"] - out["checkout_price"]
    for col in FEATURES:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        out[col] = out[col].replace([np.inf, -np.inf], np.nan)
        out[col] = out[col].fillna(out[col].median() if out[col].notna().any() else 0)
    return out[FEATURES]

def make_previous_week_baseline(history, target_rows):
    """Use same center+meal demand from the immediately prior week; fallback to historical pair mean, then global mean."""
    keys = ["center_id", "meal_id"]
    exact = history[["week", *keys, "num_orders"]].copy()
    exact["week"] = exact["week"] + 1
    exact = exact.rename(columns={"num_orders": "baseline_previous_week"})
    result = target_rows[["week", *keys]].merge(exact, on=["week", *keys], how="left")
    pair_means = history.groupby(keys)["num_orders"].mean().rename("pair_mean").reset_index()
    result = result.merge(pair_means, on=keys, how="left")
    global_mean = float(history["num_orders"].mean())
    result["baseline_previous_week"] = result["baseline_previous_week"].fillna(result["pair_mean"]).fillna(global_mean)
    return result["baseline_previous_week"].to_numpy()

# Hold out the final ten labeled weeks. Train only on earlier weeks to avoid temporal leakage.
max_week = int(train["week"].max())
validation_start = max_week - 9
fit_df = train[train["week"] < validation_start].copy()
valid_df = train[train["week"] >= validation_start].copy()
if fit_df.empty or valid_df["week"].nunique() != 10:
    raise ValueError("تعذر إنشاء تحقق زمني من آخر 10 أسابيع؛ تحقق من عمود week في train.csv.")

# A fixed seed makes the sample and results reproducible. Training uses all pre-validation rows.
# A reproducible sample keeps the exercise practical on ordinary laptops.
fit_sample = fit_df.sample(n=min(120_000, len(fit_df)), random_state=42)
model = RandomForestRegressor(
    n_estimators=30,
    max_depth=16,
    min_samples_leaf=5,
    max_features=0.9,
    random_state=42,
    n_jobs=-1,
)
model.fit(prepare_features(fit_sample), np.log1p(fit_sample["num_orders"].clip(lower=0)))
rf_predictions = np.expm1(model.predict(prepare_features(valid_df))).clip(min=0)
previous_predictions = make_previous_week_baseline(fit_df, valid_df)

# Report MAE overall and by week. MAE is in the original order-count units; lower is better.
results = pd.DataFrame({
    "id": valid_df["id"].to_numpy(),
    "week": valid_df["week"].to_numpy(),
    "actual_num_orders": valid_df["num_orders"].to_numpy(),
    "random_forest_prediction": rf_predictions,
    "previous_week_baseline": previous_predictions,
})
results.to_csv(REPORTS / "ml_validation_predictions.csv", index=False)
metrics = {
    "validation_weeks": sorted(int(x) for x in valid_df["week"].unique()),
    "training_rows_available_before_validation": int(len(fit_df)),
    "training_rows_sampled_for_model": int(len(fit_sample)),
    "validation_rows": int(len(valid_df)),
    "random_forest_mae": round(float(mean_absolute_error(valid_df["num_orders"], rf_predictions)), 3),
    "previous_week_baseline_mae": round(float(mean_absolute_error(valid_df["num_orders"], previous_predictions)), 3),
    "mae_improvement_percent_vs_baseline": round(float((mean_absolute_error(valid_df["num_orders"], previous_predictions) - mean_absolute_error(valid_df["num_orders"], rf_predictions)) / mean_absolute_error(valid_df["num_orders"], previous_predictions) * 100), 2),
    "target_transform": "log1p; predictions converted back with expm1",
    "model": "RandomForestRegressor(n_estimators=30, max_depth=16, min_samples_leaf=5, max_features=0.9, random_state=42)",
    "note": "For laptop-friendly runtime, model fitting uses reproducible random samples (up to 120,000 rows for validation and 150,000 for final test predictions). Temporal holdout: train on weeks before the final 10 training weeks, evaluate on the final 10 weeks. Test.csv has no num_orders labels, so its MAE cannot be calculated.",
}
with open(REPORTS / "ml_metrics.json", "w", encoding="utf-8") as f:
    json.dump(metrics, f, ensure_ascii=False, indent=2)
pd.DataFrame([
    {"model": "Random Forest", "MAE": metrics["random_forest_mae"]},
    {"model": "Previous-week baseline", "MAE": metrics["previous_week_baseline_mae"]},
]).to_csv(REPORTS / "ml_metrics.csv", index=False)

# Refit on all labeled training data, then generate requested future/test predictions.
final_sample = train.sample(n=min(150_000, len(train)), random_state=42)
final_model = RandomForestRegressor(
    n_estimators=30, max_depth=16, min_samples_leaf=5, max_features=0.9,
    random_state=42, n_jobs=-1,
)
final_model.fit(prepare_features(final_sample), np.log1p(final_sample["num_orders"].clip(lower=0)))
test_predictions = np.expm1(final_model.predict(prepare_features(test))).clip(min=0)
predictions = pd.DataFrame({"id": test["id"].to_numpy(), "num_orders": np.rint(test_predictions).astype("int64")})
predictions.to_csv(REPORTS / "test_predictions.csv", index=False)

# Save feature importance for interpretation.
importance = pd.DataFrame({"feature": FEATURES, "importance": final_model.feature_importances_}).sort_values("importance", ascending=False)
importance.to_csv(REPORTS / "ml_feature_importance.csv", index=False)
print("اكتمل تقييم النموذج والتنبؤ ببيانات الاختبار.")
print(json.dumps(metrics, ensure_ascii=False, indent=2))
print(f"ملف تنبؤات test.csv: {REPORTS / 'test_predictions.csv'} ({len(predictions):,} صف)")
print("تنبيه: قيم test.csv تنبؤات وليست نتائج فعلية مؤكدة.")
