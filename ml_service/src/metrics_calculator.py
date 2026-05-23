import sqlite3
import pandas as pd
import os
import json


def calculate():
    path = os.path.abspath(__file__)
    while os.path.basename(path) != "parking_3d_monitoring": path = os.path.dirname(path)
    db_path = os.path.join(path, "parking_monitoring.db")

    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT confidence, rmse, is_stationary, class_id FROM final_detections", conn)
    conn.close()

    report = {
        "avg_confidence": round(float(df['confidence'].mean()), 4),
        "localization_rmse_m": round(float(df[df['rmse'] > 0]['rmse'].mean()), 4),
        "total_stationary_objects": int(df[df['is_stationary'] == 1]['class_id'].count())
    }

    output_path = os.path.join(path, "final_metrics.json")
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

    print("Metrics calculation complete")


if __name__ == "__main__":
    calculate()