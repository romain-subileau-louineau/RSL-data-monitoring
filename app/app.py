import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def analyser(df):
    nb_rows = df.shape[0]
    nb_columns = df.shape[1]
    nb_missing_values = df.isnull().sum().sum()
    missing_values_percentage = (nb_missing_values / (nb_rows * nb_columns)) * 100
    duplicate_rows = df.duplicated().sum()
    duplicate_rows_percentage = (duplicate_rows / nb_rows) * 100
    # Convert dtype objects to strings for JSON serialisation; label booleans explicitly
    data_types = {
        col: (
            "boolean"
            if df[col].dropna().isin([True, False, 0, 1]).all()
            and df[col].nunique(dropna=True) <= 2
            else str(dtype)
        )
        for col, dtype in df.dtypes.items()
    }
    unique_values_per_column = df.nunique().to_dict()

    numeric_columns = [
        col
        for col in df.select_dtypes(include="number").columns
        if data_types[col] != "boolean"
    ]
    numeric_stats = {}
    for col in numeric_columns:
        if df[col].isnull().all():
            df[col] = 0
        else:
            s = df[col]
            numeric_stats[col] = {
                "mean": round(s.mean(), 2),
                "median": round(s.median(), 2),
                "min": round(s.min(), 2),
                "max": round(s.max(), 2),
                "q5": round(s.quantile(0.05), 2),
                "q25": round(s.quantile(0.25), 2),
                "q75": round(s.quantile(0.75), 2),
                "q95": round(s.quantile(0.95), 2),
            }

    return (
        nb_rows,
        nb_columns,
        nb_missing_values,
        missing_values_percentage,
        duplicate_rows,
        duplicate_rows_percentage,
        data_types,
        unique_values_per_column,
        numeric_stats,
    )


st.title("Data Quality Monitor")

with st.form("analysis_form"):
    uploaded_file = st.file_uploader(
        "Upload a dataset", type=["csv", "xlsx", "xls", "parquet", "json"]
    )
    has_header = st.toggle("File has a header row", value=True)
    submitted = st.form_submit_button("Analyse")

if submitted:
    df = None
    if uploaded_file is not None:
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        header_arg = 0 if has_header else None
        if ext == "csv":
            df = pd.read_csv(
                uploaded_file,
                encoding="utf-8",
                encoding_errors="replace",
                sep=None,
                engine="python",
                on_bad_lines="skip",
                quoting=3,  # csv.QUOTE_NONE — ignore unescaped quotes in values
                header=header_arg,
            )
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(uploaded_file, header=header_arg)
        elif ext == "parquet":
            df = pd.read_parquet(uploaded_file)
        elif ext == "json":
            df = pd.read_json(uploaded_file)
        else:
            st.error(f"Unsupported format: {ext}")

        # Rename numeric column indices to "Column 1, 2, ..." when no header
        if df is not None and not has_header:
            df.columns = [f"Column {i + 1}" for i in range(len(df.columns))]

    if df is not None:
        st.session_state["df"] = df
        st.session_state["input_ext"] = ext
        st.session_state["empty_rows_count"] = int(df.isna().all(axis=1).sum())

if "df" not in st.session_state:
    st.stop()

df = st.session_state["df"]
empty_rows_count = st.session_state.get("empty_rows_count", 0)
input_ext = st.session_state.get("input_ext", "csv")

if empty_rows_count > 0:
    st.warning(
        f"⚠️ {empty_rows_count} fully empty row(s) detected — excluded from analysis."
    )

# df used for analysis and fillna — excludes fully empty rows
df_analysis = df.dropna(how="all") if empty_rows_count > 0 else df

(
    nb_rows,
    nb_columns,
    nb_missing_values,
    missing_values_percentage,
    duplicate_rows,
    duplicate_rows_percentage,
    data_types,
    unique_values_per_column,
    numeric_stats,
) = analyser(df_analysis)

# Restore True/False display for columns detected as boolean
bool_cols = [col for col, dtype in data_types.items() if dtype == "boolean"]
for col in bool_cols:
    df_analysis[col] = df_analysis[col].map({1: True, 0: False})

# ── Overview ──────────────────────────────────────────────────────────────────
st.subheader("Overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", f"{nb_rows:,}")
c2.metric("Columns", nb_columns)
c3.metric(
    "Missing values",
    f"{nb_missing_values:,}",
    delta=f"{missing_values_percentage:.2f}%",
    delta_color="off",
)
c4.metric(
    "Duplicate rows",
    f"{duplicate_rows:,}",
    delta=f"{duplicate_rows_percentage:.2f}%",
    delta_color="off",
)

# ── Column summary ─────────────────────────────────────────────────────────────
st.subheader("Column summary")

# Precompute outlier counts via IQR method for numeric columns
outlier_low = {}
outlier_high = {}
for col in numeric_stats:
    s = df_analysis[col].dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    outlier_low[col] = int((s < q1 - 1.5 * iqr).sum())
    outlier_high[col] = int((s > q3 + 1.5 * iqr).sum())

summary_rows = []
for col in df_analysis.columns:
    row = {
        "Column": col,
        "Type": data_types.get(col, ""),
        "Missing": df_analysis[col].isna().sum(),
        "Missing %": f"{df_analysis[col].isna().mean() * 100:.2f}%",
        "Unique": unique_values_per_column.get(col, ""),
    }
    if col in numeric_stats:
        s = numeric_stats[col]
        row |= {
            "Min": s["min"],
            "Q5": s["q5"],
            "Q25": s["q25"],
            "Median": s["median"],
            "Mean": s["mean"],
            "Q75": s["q75"],
            "Q95": s["q95"],
            "Max": s["max"],
            "Outliers <": outlier_low.get(col, 0),
            "Outliers >": outlier_high.get(col, 0),
        }
    summary_rows.append(row)

summary_df = pd.DataFrame(summary_rows).set_index("Column")
missing_pct_raw = df_analysis.isna().mean() * 100
unique_raw = df_analysis.nunique()


def _style_summary(row):
    styles = []
    for col in summary_df.columns:
        if col == "Missing %":
            pct = missing_pct_raw.get(row.name, 0)
            if pct == 100:
                styles.append("background-color: #f44336; color: white")
            elif pct >= 50:
                styles.append("background-color: #ff9800; color: white")
            else:
                styles.append("")
        elif col == "Unique" and unique_raw.get(row.name, 0) == 1:
            styles.append("background-color: #ff9800; color: white")
        elif (
            col == "Outliers <"
            and outlier_low.get(row.name, 0) > 0
            or col == "Outliers >"
            and outlier_high.get(row.name, 0) > 0
        ):
            styles.append("background-color: #f44336; color: white")
        else:
            styles.append("")
    return styles


numeric_display_cols = ["Min", "Q5", "Q25", "Median", "Mean", "Q75", "Q95", "Max"]
fmt = {col: "{:.2f}" for col in numeric_display_cols if col in summary_df.columns}
fmt |= {
    col: "{:.0f}" for col in ["Outliers <", "Outliers >"] if col in summary_df.columns
}

st.dataframe(
    summary_df.style.apply(_style_summary, axis=1).format(fmt, na_rep=""),
    use_container_width=True,
)

# ── Data preview ──────────────────────────────────────────────────────────────
st.subheader("Data preview")
preview_col1, preview_col2 = st.columns([1, 3])
with preview_col1:
    preview_mode = st.radio("Show", ["Head", "Tail"], horizontal=True)
with preview_col2:
    preview_n = st.slider("Number of rows", min_value=1, max_value=10, value=5)
all_preview_cols = list(df_analysis.columns)
selected_cols = st.multiselect(
    "Columns to display (max 10)",
    options=all_preview_cols,
    default=all_preview_cols[:10],
)
selected_cols = selected_cols[:10]

st.markdown("**Filters**")
NUM_FILTERS = 3
NONE_OPTION = "—"
filtered_df = df_analysis.copy()
for i in range(NUM_FILTERS):
    fcol1, fcol2, fcol3 = st.columns([3, 2, 3])
    with fcol1:
        f_col = st.selectbox(
            "Column",
            [NONE_OPTION] + all_preview_cols,
            key=f"f_col_{i}",
            label_visibility="collapsed",
        )
    if f_col == NONE_OPTION:
        with fcol2:
            st.selectbox("Op", ["—"], key=f"f_op_{i}", label_visibility="collapsed")
        with fcol3:
            st.text_input(
                "Value", key=f"f_val_{i}", label_visibility="collapsed", disabled=True
            )
        continue
    is_num = pd.api.types.is_numeric_dtype(df_analysis[f_col])
    ops = [">", ">=", "<", "<=", "==", "!="] if is_num else ["==", "!=", "contains"]
    with fcol2:
        f_op = st.selectbox("Op", ops, key=f"f_op_{i}", label_visibility="collapsed")
    with fcol3:
        f_val = st.text_input("Value", key=f"f_val_{i}", label_visibility="collapsed")
    if f_val == "":
        continue
    try:
        if is_num:
            num_val = float(f_val)
            if f_op == ">":
                filtered_df = filtered_df[filtered_df[f_col] > num_val]
            elif f_op == ">=":
                filtered_df = filtered_df[filtered_df[f_col] >= num_val]
            elif f_op == "<":
                filtered_df = filtered_df[filtered_df[f_col] < num_val]
            elif f_op == "<=":
                filtered_df = filtered_df[filtered_df[f_col] <= num_val]
            elif f_op == "==":
                filtered_df = filtered_df[filtered_df[f_col] == num_val]
            elif f_op == "!=":
                filtered_df = filtered_df[filtered_df[f_col] != num_val]
        else:
            if f_op == "==":
                filtered_df = filtered_df[filtered_df[f_col].astype(str) == f_val]
            elif f_op == "!=":
                filtered_df = filtered_df[filtered_df[f_col].astype(str) != f_val]
            elif f_op == "contains":
                filtered_df = filtered_df[
                    filtered_df[f_col].astype(str).str.contains(f_val, na=False)
                ]
    except Exception:
        st.warning(f"Filter {i + 1} is invalid.")

preview_df = filtered_df[selected_cols] if selected_cols else filtered_df
st.caption(f"{len(filtered_df)} row(s) after filtering")
st.dataframe(
    preview_df.head(preview_n) if preview_mode == "Head" else preview_df.tail(preview_n)
)

# ── Missing data heatmap ───────────────────────────────────────────────────────
st.subheader("Missing data map")
missing_mask = df.isna().astype(int).values.tolist()
fig = go.Figure(
    go.Heatmap(
        z=missing_mask,
        x=list(df.columns),
        colorscale=[[0, "#4CAF50"], [1, "#F44336"]],
        showscale=True,
        colorbar=dict(tickvals=[0, 1], ticktext=["Present", "Missing"], thickness=15),
        zmin=0,
        zmax=1,
    )
)
fig.update_layout(
    xaxis_title="Columns",
    yaxis_title="Rows",
    yaxis=dict(autorange="reversed"),
    height=max(300, min(800, len(df) * 8)),
    margin=dict(l=40, r=40, t=20, b=40),
)
st.plotly_chart(fig, use_container_width=True)

# ── Fill missing values ────────────────────────────────────────────────────────
st.subheader("Fill missing values")
cols_with_na = [col for col in df_analysis.columns if df_analysis[col].isna().any()]
if not cols_with_na:
    st.info("No missing values to fill.")
else:
    col_to_fill = st.selectbox("Column to fill", cols_with_na)
    is_bool = col_to_fill in bool_cols
    is_numeric = (
        pd.api.types.is_numeric_dtype(df_analysis[col_to_fill])
        if col_to_fill
        else False
    ) and not is_bool

    with st.form("fillna_form"):
        if is_bool:
            fill_mode = st.radio("Fill with", ["True", "False"])
        elif is_numeric:
            col_mean = round(df_analysis[col_to_fill].mean(), 2)
            col_median = round(df_analysis[col_to_fill].median(), 2)
            fill_mode = st.radio(
                "Fill with", [f"Mean ({col_mean})", f"Median ({col_median})", "0"]
            )
        else:
            fill_mode = st.radio("Fill with", ["other", "missing"])
        fill_submitted = st.form_submit_button("Apply")

    if fill_submitted and col_to_fill:
        is_bool = col_to_fill in bool_cols
        is_numeric = (
            pd.api.types.is_numeric_dtype(df_analysis[col_to_fill]) and not is_bool
        )
        if is_bool:
            fill_value = fill_mode == "True"
        elif fill_mode.startswith("Mean"):
            fill_value = df_analysis[col_to_fill].mean()
        elif fill_mode.startswith("Median"):
            fill_value = df_analysis[col_to_fill].median()
        else:
            fill_value = 0 if (is_numeric and fill_mode == "0") else fill_mode
        st.session_state["df"][col_to_fill] = df[col_to_fill].fillna(fill_value)
        st.success(f"Column **{col_to_fill}** filled with `{fill_value}`.")
        st.rerun()

# ── Interactive plot ───────────────────────────────────────────────────────────
st.subheader("Interactive plot")
all_cols = list(df_analysis.columns)
pcol1, pcol2, pcol3 = st.columns(3)
with pcol1:
    x_col = st.selectbox("X axis", all_cols, key="plot_x")
with pcol2:
    y_col = st.selectbox(
        "Y axis", all_cols, index=min(1, len(all_cols) - 1), key="plot_y"
    )
with pcol3:
    plot_type = st.selectbox(
        "Chart type", ["Scatter", "Bar", "Line", "Box", "Histogram"], key="plot_type"
    )

if plot_type == "Scatter":
    pfig = px.scatter(df_analysis, x=x_col, y=y_col)
elif plot_type == "Bar":
    pfig = px.bar(df_analysis, x=x_col, y=y_col)
elif plot_type == "Line":
    pfig = px.line(df_analysis, x=x_col, y=y_col)
elif plot_type == "Box":
    pfig = px.box(df_analysis, x=x_col, y=y_col)
elif plot_type == "Histogram":
    pfig = px.histogram(df_analysis, x=x_col)
st.plotly_chart(pfig, use_container_width=True)

# ── Download ───────────────────────────────────────────────────────────────────
st.subheader("Download modified dataset")
drop_empty_on_export = st.toggle(
    "Remove fully empty rows on export",
    value=False,
    disabled=empty_rows_count == 0,
)
df_export = df.dropna(how="all") if drop_empty_on_export else df

MIME_MAP = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "parquet": "application/octet-stream",
    "json": "application/json",
}
EXPORT_FORMATS = ["csv", "xlsx", "parquet", "json"]
export_ext = st.selectbox(
    "Export format",
    EXPORT_FORMATS,
    index=EXPORT_FORMATS.index(input_ext) if input_ext in EXPORT_FORMATS else 0,
)

if export_ext == "csv":
    export_data = df_export.to_csv(index=False).encode("utf-8")
elif export_ext == "xlsx":
    buf = io.BytesIO()
    df_export.to_excel(buf, index=False)
    export_data = buf.getvalue()
elif export_ext == "parquet":
    buf = io.BytesIO()
    df_export.to_parquet(buf, index=False)
    export_data = buf.getvalue()
elif export_ext == "json":
    export_data = df_export.to_json(orient="records", force_ascii=False).encode("utf-8")

st.download_button(
    f"Download ({export_ext.upper()})",
    data=export_data,
    file_name=f"dataset_modified.{export_ext}",
    mime=MIME_MAP.get(export_ext, "application/octet-stream"),
)

# ── Personal rules ─────────────────────────────────────────────────────────────
st.subheader("Personal rules")

if "rules" not in st.session_state:
    st.session_state["rules"] = []

RULE_TYPES = [
    "No missing values",
    "Missing % ≤",
    "No duplicates",
    "Unique count ==",
    "Unique count ≥",
    "Unique count ≤",
    "Values in",
    "All values ≥",
    "All values ≤",
    "Between",
    "Min ≥",
    "Max ≤",
    "Mean ≥",
    "Mean ≤",
    "Std ≤",
    "No outliers (IQR)",
]
NUMERIC_RULES = {
    "All values ≥",
    "All values ≤",
    "Min ≥",
    "Max ≤",
    "Mean ≥",
    "Mean ≤",
    "Std ≤",
    "No outliers (IQR)",
    "Between",
}
NO_THRESHOLD_RULES = {"No missing values", "No outliers (IQR)", "No duplicates"}
STRING_THRESHOLD_RULES = {"Values in", "Between"}

with st.form("add_rule_form"):
    rc1, rc2, rc3 = st.columns([3, 3, 2])
    with rc1:
        rule_col = st.selectbox("Column", list(df_analysis.columns), key="rule_col")
    with rc2:
        is_num_col = (
            pd.api.types.is_numeric_dtype(df_analysis[rule_col])
            and rule_col not in bool_cols
        )
        available_rules = (
            RULE_TYPES
            if is_num_col
            else [r for r in RULE_TYPES if r not in NUMERIC_RULES]
        )
        rule_type = st.selectbox("Rule", available_rules, key="rule_type")
    with rc3:
        needs_threshold = rule_type not in NO_THRESHOLD_RULES
        hint = {
            "Between": "min,max e.g. 0,100 or 0.1,0.3",
            "Values in": "val1,val2,... e.g. A,B,C",
        }.get(rule_type, "")
        threshold = st.text_input(
            "Threshold",
            disabled=not needs_threshold,
            key="rule_threshold",
        )
        if hint:
            st.caption(hint)
    add_rule = st.form_submit_button("Add rule")

if add_rule:
    if rule_type not in NO_THRESHOLD_RULES and threshold == "":
        st.warning("Please enter a threshold value.")
    else:
        try:
            if rule_type in NO_THRESHOLD_RULES:
                thr = None
            elif rule_type in STRING_THRESHOLD_RULES:
                thr = threshold.strip()
            else:
                thr = float(threshold)
            st.session_state["rules"].append(
                {"col": rule_col, "type": rule_type, "threshold": thr}
            )
        except ValueError:
            st.warning("Threshold must be a number.")

# Display and remove rules
rules = st.session_state["rules"]
if rules:
    for i, rule in enumerate(rules):
        thr_str = f" {rule['threshold']}" if rule["threshold"] is not None else ""
        label = f"**{rule['col']}** — {rule['type']}{thr_str}"
        rcol1, rcol2 = st.columns([10, 1])
        with rcol1:
            st.markdown(label)
        with rcol2:
            if st.button("✕", key=f"del_rule_{i}"):
                st.session_state["rules"].pop(i)
                st.rerun()

    # Evaluate rules
    st.markdown("#### Results")
    results = []
    for rule in rules:
        col, rtype, thr = rule["col"], rule["type"], rule["threshold"]
        series = df_analysis[col]
        if rtype == "No missing values":
            actual = series.isna().sum()
            passed = actual == 0
            detail = f"{actual} missing value(s)"
        elif rtype == "Missing % ≤":
            actual = series.isna().mean() * 100
            passed = actual <= thr
            detail = f"{actual:.2f}% missing (limit {thr}%)"
        elif rtype == "No duplicates":
            actual = series.duplicated().sum()
            passed = actual == 0
            detail = f"{actual} duplicate(s)"
        elif rtype == "Unique count ==":
            actual = series.nunique()
            passed = actual == int(thr)
            detail = f"{actual} unique (expected {int(thr)})"
        elif rtype == "Unique count ≥":
            actual = series.nunique()
            passed = actual >= int(thr)
            detail = f"{actual} unique (expected ≥ {int(thr)})"
        elif rtype == "Unique count ≤":
            actual = series.nunique()
            passed = actual <= int(thr)
            detail = f"{actual} unique (expected ≤ {int(thr)})"
        elif rtype == "Values in":
            allowed = {v.strip() for v in thr.split(",")}
            invalid = set(series.dropna().astype(str).unique()) - allowed
            passed = len(invalid) == 0
            detail = (
                f"{len(invalid)} unexpected value(s): {', '.join(list(invalid)[:5])}"
            )
        elif rtype == "All values ≥":
            violations = (series.dropna() < thr).sum()
            passed = violations == 0
            detail = f"{violations} value(s) below {thr}"
        elif rtype == "All values ≤":
            violations = (series.dropna() > thr).sum()
            passed = violations == 0
            detail = f"{violations} value(s) above {thr}"
        elif rtype == "Between":
            lo, hi = (float(v.strip()) for v in thr.split(","))
            below = (series.dropna() < lo).sum()
            above = (series.dropna() > hi).sum()
            passed = below == 0 and above == 0
            detail = f"{below} below {lo}, {above} above {hi}"
        elif rtype == "Min ≥":
            actual = series.min()
            passed = actual >= thr
            detail = f"min = {actual} (expected ≥ {thr})"
        elif rtype == "Max ≤":
            actual = series.max()
            passed = actual <= thr
            detail = f"max = {actual} (expected ≤ {thr})"
        elif rtype == "Mean ≥":
            actual = round(series.mean(), 2)
            passed = actual >= thr
            detail = f"mean = {actual} (expected ≥ {thr})"
        elif rtype == "Mean ≤":
            actual = round(series.mean(), 2)
            passed = actual <= thr
            detail = f"mean = {actual} (expected ≤ {thr})"
        elif rtype == "Std ≤":
            actual = round(series.std(), 2)
            passed = actual <= thr
            detail = f"std = {actual} (expected ≤ {thr})"
        elif rtype == "No outliers (IQR)":
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            actual = int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())
            passed = actual == 0
            detail = f"{actual} outlier(s) detected"
        results.append(
            {
                "Column": col,
                "Rule": f"{rtype}{f' {thr}' if thr is not None else ''}",
                "Status": "✅ Pass" if passed else "❌ Fail",
                "Detail": detail,
            }
        )

    results_df = pd.DataFrame(results)

    def _color_status(val):
        if "Pass" in val:
            return "background-color: #4CAF50; color: white"
        return "background-color: #f44336; color: white"

    st.dataframe(
        results_df.style.map(_color_status, subset=["Status"]),
        use_container_width=True,
        hide_index=True,
    )

    passed_count = sum(1 for r in results if "Pass" in r["Status"])
    st.caption(f"{passed_count}/{len(results)} rule(s) passing")
else:
    st.info("No rules defined yet. Add a rule above.")
