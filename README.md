# Data Quality Monitor

> Interactive Streamlit app for dataset profiling, quality analysis, missing-value imputation, and custom rule validation.

Upload any tabular file and instantly get a full quality report: column statistics, outlier detection, missing data heatmap, and a pass/fail summary of your own business rules — all in one page.

## Features

| Section | Description |
|---|---|
| **Overview** | Row count, column count, missing values %, duplicate rows % |
| **Column summary** | Type, missing %, unique count, min/Q5/Q25/median/mean/Q75/Q95/max, IQR outlier counts — colour-coded (red/orange alerts) |
| **Data preview** | Head or tail, column selector (max 10), up to 3 row filters with numeric (`>`, `>=`, `<`, `<=`, `==`, `!=`) and categorical (`==`, `!=`, `contains`) operators |
| **Missing data heatmap** | Interactive green/red grid across the entire dataset including fully empty rows |
| **Fill missing values** | Mean/median/0 for numeric, True/False for boolean, `other`/`missing` for categorical — actual values shown in labels |
| **Interactive plot** | Scatter, bar, line, box, or histogram with free X/Y axis selection |
| **Personal rules** | Custom assertions per column (no missing, missing % ≤, all values ≥/≤, min ≥, max ≤) with a colour-coded pass/fail table |
| **Export** | Download the modified dataset as CSV, XLSX, Parquet, or JSON with an optional empty-row removal |

## Supported input formats

`CSV` · `XLSX` · `XLS` · `Parquet` · `JSON`

## Getting started

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the app
streamlit run app/app.py
```

The app opens in your browser at `http://localhost:8501`.

## Deploy to Streamlit Community Cloud

1. Push this folder to a public GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Set **Main file path** to `app/app.py`
4. Click **Deploy**

## Project structure

```
app/
  app.py              # single-file Streamlit application (all logic inlined)
requirements.txt      # pinned Python dependencies
```

## License

MIT — see [LICENSE](LICENSE).
