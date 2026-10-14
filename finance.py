import json
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_FILE = "data.json"

# Configurazione pagina Streamlit
st.set_page_config(
    page_title="Dashboard Patrimonio & Finanze",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Tema scuro / moderno)
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 1.5rem !important;
        }
        h1, h2, h3 {
            padding-top: 0.2rem !important;
            padding-bottom: 0.4rem !important;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 1rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_data():
    """Carica i dati dal file locale data.json."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.sidebar.error(f"Errore nella lettura di {DATA_FILE}: {e}")
        return {}


def save_data(data_to_save):
    """Salva i dati forniti nel file locale data.json."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=4, ensure_ascii=False)


def generate_future_months(last_mese_str: str, num_months: int):
    """Genera le etichette dei mesi futuri a partire dall'ultimo mese presente."""
    future_labels = []
    formats_to_try = ["%m/%y", "%m/%Y", "%Y-%m", "%Y/%m"]
    for fmt in formats_to_try:
        try:
            dt = pd.to_datetime(last_mese_str, format=fmt)
            for i in range(1, num_months + 1):
                next_dt = dt + pd.DateOffset(months=i)
                future_labels.append(next_dt.strftime(fmt))
            return future_labels
        except ValueError:
            continue
    return [f"+{i}m" for i in range(1, num_months + 1)]


# Caricamento iniziale dei dati
data = load_data()

# Sidebar - Gestione File JSON
st.sidebar.title("⚙️ Gestione Dati")
st.sidebar.markdown(
    "Puoi caricare un file `.json` personalizzato o scaricare la struttura corrente."
)

uploaded_file = st.sidebar.file_uploader("Carica file JSON", type=["json"])

if uploaded_file is not None:
    try:
        data = json.load(uploaded_file)
        save_data(data)
        st.sidebar.success("Dati caricati e salvati in local data.json!")
    except Exception as e:
        st.sidebar.error(f"Errore nel parsing del JSON: {e}")

st.sidebar.download_button(
    label="📥 Scarica Modello JSON",
    data=json.dumps(data, indent=4),
    file_name="dati_patrimonio.json",
    mime="application/json",
)

# Header Principale
st.title("💼 Dashboard Finanziaria Personale")
st.markdown(
    "Monitoraggio in tempo reale di patrimonio, PAC/fondi pensione e prestiti in corso."
)

# Struttura a Schede (Tabs)
tab1, tab2, tab3 = st.tabs(
    ["📊 Patrimonio Netto", "📈 PAC & Fondi Pensione", "💳 Prestiti & Debiti"]
)

# ----------------------------------------------------
# TAB 1: PATRIMONIO NETTO
# ----------------------------------------------------
with tab1:
    st.header("Calcolo e Crescita Patrimonio")

    df_base = pd.DataFrame(data.get("patrimonio", []))
    if df_base.empty:
        df_base = pd.DataFrame(
            columns=[
                "mese",
                "fineco_fondo",
                "fonchim_fondo",
                "fineco_portafoglio",
            ]
        )

    # Recupero dati correnti da session_state per reattività immediata
    if "editor_patrimonio_tab1" in st.session_state:
        edited_data = st.session_state["editor_patrimonio_tab1"]
        df_patrimonio = df_base.copy()

        for row_idx, changes in edited_data.get("edited_rows", {}).items():
            for col, val in changes.items():
                df_patrimonio.loc[row_idx, col] = val

        for new_row in edited_data.get("added_rows", []):
            df_patrimonio = pd.concat(
                [df_patrimonio, pd.DataFrame([new_row])], ignore_index=True
            )

        deleted_indices = edited_data.get("deleted_rows", [])
        if deleted_indices:
            df_patrimonio = df_patrimonio.drop(index=deleted_indices).reset_index(
                drop=True
            )
    else:
        df_patrimonio = df_base.copy()

    # Conversione numerica sicura
    df_patrimonio["fineco_fondo"] = pd.to_numeric(
        df_patrimonio["fineco_fondo"], errors="coerce"
    ).fillna(0.0)
    df_patrimonio["fonchim_fondo"] = pd.to_numeric(
        df_patrimonio["fonchim_fondo"], errors="coerce"
    ).fillna(0.0)
    df_patrimonio["fineco_portafoglio"] = pd.to_numeric(
        df_patrimonio["fineco_portafoglio"], errors="coerce"
    ).fillna(0.0)
    df_patrimonio = df_patrimonio[
        df_patrimonio["mese"].astype(str).str.strip() != ""
    ]

    # 1. RIASSUNTO METRICHE
    if not df_patrimonio.empty:
        df_patrimonio["Totale"] = (
            df_patrimonio["fineco_fondo"]
            + df_patrimonio["fonchim_fondo"]
            + df_patrimonio["fineco_portafoglio"]
        )
        df_patrimonio["Diff_Mese_Prec"] = (
            df_patrimonio["Totale"].diff().fillna(0)
        )

        ultimo_mese = df_patrimonio.iloc[-1]
        penultimo_mese = (
            df_patrimonio.iloc[-2] if len(df_patrimonio) > 1 else ultimo_mese
        )

        def get_diff(curr, prev):
            return float(curr - prev)

        diff_totale = get_diff(ultimo_mese["Totale"], penultimo_mese["Totale"])
        diff_fineco_fondo = get_diff(
            ultimo_mese["fineco_fondo"], penultimo_mese["fineco_fondo"]
        )
        diff_fonchim_fondo = get_diff(
            ultimo_mese["fonchim_fondo"], penultimo_mese["fonchim_fondo"]
        )
        diff_fineco_port = get_diff(
            ultimo_mese["fineco_portafoglio"],
            penultimo_mese["fineco_portafoglio"],
        )

        def fmt_delta(diff, prev):
            perc = (diff / prev * 100) if prev != 0 else 0
            if diff < 0:
                return f"-€ {abs(diff):,.2f} ({perc:.2f}%)"
            else:
                return f"€ {diff:,.2f} (+{perc:.2f}%)"

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Patrimonio Totale",
                f"€ {ultimo_mese['Totale']:,.2f}",
                fmt_delta(diff_totale, penultimo_mese["Totale"]),
                delta_color="normal",
            )
        with col2:
            st.metric(
                "Fondo Pensione Fineco",
                f"€ {ultimo_mese['fineco_fondo']:,.2f}",
                fmt_delta(diff_fineco_fondo, penultimo_mese["fineco_fondo"]),
                delta_color="normal",
            )
        with col3:
            st.metric(
                "Fondo Pensione Fonchim",
                f"€ {ultimo_mese['fonchim_fondo']:,.2f}",
                fmt_delta(diff_fonchim_fondo, penultimo_mese["fonchim_fondo"]),
                delta_color="normal",
            )
        with col4:
            st.metric(
                "Portafoglio Fineco",
                f"€ {ultimo_mese['fineco_portafoglio']:,.2f}",
                fmt_delta(diff_fineco_port, penultimo_mese["fineco_portafoglio"]),
                delta_color="normal",
            )

        st.markdown("---")

        # 2. TITOLO GRAFICO E CONTROLLO ANNI DI PROIEZIONE AFFIANCATI
        col_hdr_left, col_hdr_right = st.columns([3, 1])
        with col_hdr_left:
            st.subheader("Andamento Patrimonio e Proiezione Futura (Grado 2)")
        with col_hdr_right:
            anni_proiezione = st.number_input(
                "Anni di proiezione futura",
                min_value=0,
                max_value=10,
                value=2,
                step=1,
                help="Inserisci quanti anni estendere la proiezione della tendenza",
            )

        degree = 2  # Grado fissato permanentemente a 2
        mesi_proiezione = int(anni_proiezione * 12)
        n_storico = len(df_patrimonio)

        col_chart1, col_chart2 = st.columns([2, 1])

        with col_chart1:
            fig_trend = go.Figure()

            # Traccia patrimonio effettivo
            fig_trend.add_trace(
                go.Scatter(
                    x=np.arange(n_storico),
                    y=df_patrimonio["Totale"],
                    mode="lines+markers",
                    name="Patrimonio Totale",
                    line=dict(color="#38BDF8", width=3),
                    marker=dict(size=8),
                )
            )

            # --- CURVA POLINOMIALE DI TENDENZA E PROIEZIONE ---
            if n_storico >= 2:
                x_numeric = np.arange(n_storico)
                y_vals = df_patrimonio["Totale"].values.astype(float)

                eff_degree = min(degree, n_storico - 1)
                poly_coeffs = np.polyfit(x_numeric, y_vals, eff_degree)
                poly_func = np.poly1d(poly_coeffs)

                # Generazione etichette mesi (Storico + Futuro)
                ultimo_mese_str = str(df_patrimonio["mese"].iloc[-1])
                mesi_futuri = generate_future_months(
                    ultimo_mese_str, mesi_proiezione
                )
                tutti_i_mesi = list(df_patrimonio["mese"]) + mesi_futuri

                max_x = (n_storico - 1) + mesi_proiezione
                x_smooth = np.linspace(
                    0, max_x, max(100, (n_storico + mesi_proiezione) * 10)
                )
                y_smooth = poly_func(x_smooth)

                fig_trend.add_trace(
                    go.Scatter(
                        x=x_smooth,
                        y=y_smooth,
                        mode="lines",
                        name="Tendenza Polinomiale e Proiezione",
                        line=dict(color="#F59E0B", width=2.5, dash="dash"),
                    )
                )

                if mesi_proiezione > 0:
                    fig_trend.add_vrect(
                        x0=n_storico - 1,
                        x1=max_x,
                        fillcolor="rgba(245, 158, 11, 0.1)",
                        layer="below",
                        line_width=0,
                        annotation_text="Proiezione Futura",
                        annotation_position="top left",
                    )

            fig_trend.update_layout(
                title="Evoluzione del Patrimonio Netto",
                xaxis=dict(
                    tickmode="array",
                    tickvals=np.arange(len(tutti_i_mesi)),
                    ticktext=tutti_i_mesi,
                    title="Mese",
                ),
                yaxis_title="Valore (€)",
                template="plotly_dark",
                height=400,
            )
            st.plotly_chart(fig_trend, use_container_width=True)

            if anni_proiezione > 0 and n_storico >= 2:
                valore_proiettato = poly_func(max_x)
                valore_attuale = y_vals[-1]
                differenza = valore_proiettato - valore_attuale

                c_p1, c_p2, c_p3 = st.columns(3)
                c_p1.metric("Patrimonio Attuale", f"€ {valore_attuale:,.2f}")
                c_p2.metric(
                    f"Stima a {anni_proiezione} Anni",
                    f"€ {valore_proiettato:,.2f}",
                )
                c_p3.metric(
                    "Variazione Stimata",
                    f"€ {differenza:+,.2f}",
                    delta_color="normal",
                )

        with col_chart2:
            fig_diff = px.bar(
                df_patrimonio,
                x="mese",
                y="Diff_Mese_Prec",
                title="Variazione Mensile Totale (€)",
                color="Diff_Mese_Prec",
                color_continuous_scale=["#EF4444", "#10B981"],
                template="plotly_dark",
            )
            fig_diff.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_diff, use_container_width=True)

        st.markdown("---")

    # 3. TABELLA MODIFICABILE PATRIMONIO
    st.subheader("Dettaglio Storico e Inserimento Dati")
    st.caption(
        "Modifica le celle o aggiungi nuove righe con il tasto '+': i grafici e i dettagli si aggiorneranno automaticamente."
    )

    edited_patrimonio = st.data_editor(
        df_base[
            ["mese", "fineco_fondo", "fonchim_fondo", "fineco_portafoglio"]
        ],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "mese": st.column_config.TextColumn("Mese", required=True),
            "fineco_fondo": st.column_config.NumberColumn(
                "Fondo Fineco (€)", min_value=0.0, format="%.2f €", default=0.0
            ),
            "fonchim_fondo": st.column_config.NumberColumn(
                "Fondo Fonchim (€)", min_value=0.0, format="%.2f €", default=0.0
            ),
            "fineco_portafoglio": st.column_config.NumberColumn(
                "Portafoglio Fineco (€)",
                min_value=0.0,
                format="%.2f €",
                default=0.0,
            ),
        },
        key="editor_patrimonio_tab1",
    )

    if st.button("💾 Salva Modifiche Patrimonio nel JSON", type="primary"):
        records = edited_patrimonio.to_dict(orient="records")
        cleaned_records = []
        for r in records:
            if r.get("mese") and str(r["mese"]).strip():
                cleaned_records.append(
                    {
                        "mese": str(r["mese"]).strip(),
                        "fineco_fondo": float(r.get("fineco_fondo") or 0.0),
                        "fonchim_fondo": float(r.get("fonchim_fondo") or 0.0),
                        "fineco_portafoglio": float(
                            r.get("fineco_portafoglio") or 0.0
                        ),
                    }
                )

        data["patrimonio"] = cleaned_records
        save_data(data)
        st.success("File JSON salvato con successo!")
        st.rerun()

# ----------------------------------------------------
# TAB 2: PAC & FONDI PENSIONE
# ----------------------------------------------------
with tab2:
    st.header("Piani di Accumulo (PAC) e Fondi Pensione")

    invest_dict = data.get("investimenti", {})

    if invest_dict:
        selected_invest = st.selectbox(
            "Seleziona Strumento / Fondo", list(invest_dict.keys())
        )

        raw_fondo = invest_dict.get(selected_invest, {})

        if isinstance(raw_fondo, dict):
            val_attuale_json = float(raw_fondo.get("valore_attuale", 0.0))
            raw_data = raw_fondo.get("movimenti", [])
        else:
            val_attuale_json = 0.0
            raw_data = raw_fondo if isinstance(raw_fondo, list) else []

        df_base_inv = pd.DataFrame(raw_data)

        required_cols = ["data", "quote", "valore_quota", "importo"]
        for col in required_cols:
            if col not in df_base_inv.columns:
                df_base_inv[col] = 0.0 if col != "data" else ""

        editor_key = f"editor_inv_{selected_invest}"

        if editor_key in st.session_state:
            edited_data = st.session_state[editor_key]
            df_inv = df_base_inv.copy()

            for row_idx, changes in edited_data.get("edited_rows", {}).items():
                for col, val in changes.items():
                    df_inv.loc[row_idx, col] = val

            for new_row in edited_data.get("added_rows", []):
                df_inv = pd.concat(
                    [df_inv, pd.DataFrame([new_row])], ignore_index=True
                )

            deleted_indices = edited_data.get("deleted_rows", [])
            if deleted_indices:
                df_inv = df_inv.drop(index=deleted_indices).reset_index(
                    drop=True
                )
        else:
            df_inv = df_base_inv.copy()

        df_inv["quote"] = pd.to_numeric(
            df_inv["quote"], errors="coerce"
        ).fillna(0.0)
        df_inv["valore_quota"] = pd.to_numeric(
            df_inv["valore_quota"], errors="coerce"
        ).fillna(0.0)
        df_inv["importo"] = pd.to_numeric(
            df_inv["importo"], errors="coerce"
        ).fillna(0.0)

        mask_importo_zero = (
            (df_inv["importo"] == 0.0)
            & (df_inv["quote"] > 0)
            & (df_inv["valore_quota"] > 0)
        )
        df_inv.loc[mask_importo_zero, "importo"] = (
            df_inv["quote"] * df_inv["valore_quota"]
        )

        df_inv_clean = df_inv[
            df_inv["data"].astype(str).str.strip() != ""
        ].copy()

        if val_attuale_json > 0:
            default_val_attuale = val_attuale_json
        elif (
            not df_inv_clean.empty and df_inv_clean["valore_quota"].iloc[-1] > 0
        ):
            default_val_attuale = float(df_inv_clean["valore_quota"].iloc[-1])
        else:
            default_val_attuale = 100.0

        valore_attuale = st.number_input(
            "Valore Attuale Quota (€)",
            min_value=0.0,
            value=default_val_attuale,
            step=0.01,
            format="%.4f",
            key=f"val_attuale_{selected_invest}",
        )

        if not df_inv_clean.empty:
            df_inv_clean["rendimento"] = df_inv_clean["valore_quota"].apply(
                lambda vq: (
                    ((valore_attuale / vq) - 1) * 100 if vq > 0 else 0.0
                )
            )
        else:
            df_inv_clean["rendimento"] = 0.0

        tot_investito = df_inv_clean["importo"].sum()
        tot_quote = df_inv_clean["quote"].sum()
        valore_totale_fondo = tot_quote * valore_attuale
        guadagno_ass = valore_totale_fondo - tot_investito
        rend_medio = (
            df_inv_clean["rendimento"].mean() if not df_inv_clean.empty else 0.0
        )

        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

        with col_m1:
            st.metric("Totale Versato", f"€ {tot_investito:,.2f}")

        with col_m2:
            st.metric("Totale Quote", f"{tot_quote:,.3f}")

        with col_m3:
            st.metric("Valore Totale Fondo", f"€ {valore_totale_fondo:,.2f}")

        with col_m4:
            color_guadagno = "#10B981" if guadagno_ass >= 0 else "#EF4444"
            st.markdown(
                f"""
                <div style="text-align: left;">
                    <p style="font-size: 14px; margin-bottom: 4px; color: #9CA3AF; font-family: Source Sans Pro, sans-serif;">Guadagno / Perdita</p>
                    <p style="font-size: 36px; font-weight: 600; margin-top: 0px; margin-bottom: 0px; color: {color_guadagno}; font-family: Source Sans Pro, sans-serif;">
                        € {guadagno_ass:+,.2f}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_m5:
            color_rend = "#10B981" if rend_medio >= 0 else "#EF4444"
            st.markdown(
                f"""
                <div style="text-align: left;">
                    <p style="font-size: 14px; margin-bottom: 4px; color: #9CA3AF; font-family: Source Sans Pro, sans-serif;">Rendimento Medio</p>
                    <p style="font-size: 36px; font-weight: 600; margin-top: 0px; margin-bottom: 0px; color: {color_rend}; font-family: Source Sans Pro, sans-serif;">
                        {rend_medio:+.2f}%
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not df_inv_clean.empty:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_quota = px.line(
                    df_inv_clean,
                    x="data",
                    y="valore_quota",
                    title=f"Andamento Valore Quota d'Acquisto - {selected_invest}",
                    markers=True,
                    template="plotly_dark",
                )
                fig_quota.update_traces(
                    line_color="#F59E0B", name="Prezzo d'Acquisto"
                )

                fig_quota.add_hline(
                    y=valore_attuale,
                    line_dash="dash",
                    line_color="#38BDF8",
                    annotation_text=f"Valore Attuale: € {valore_attuale:.4f}",
                    annotation_position="top left",
                    annotation_font_color="#38BDF8",
                )

                st.plotly_chart(fig_quota, use_container_width=True)

            with col_g2:
                fig_rend = px.line(
                    df_inv_clean,
                    x="data",
                    y="rendimento",
                    title=f"Rendimento nel Tempo vs Valore Attuale (€ {valore_attuale:.4f})",
                    markers=True,
                    template="plotly_dark",
                )
                fig_rend.update_traces(line_color="#10B981")

                fig_rend.add_hline(y=0, line_dash="dot", line_color="#9CA3AF")

                st.plotly_chart(fig_rend, use_container_width=True)

        st.subheader(f"Dettaglio e Inserimento Movimenti: {selected_invest}")
        st.caption(
            "Inserisci/modifica i versamenti. Il rendimento viene calcolato automaticamente in base al 'Valore Attuale Quota'."
        )

        edited_inv = st.data_editor(
            df_base_inv[["data", "quote", "valore_quota", "importo"]],
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "data": st.column_config.TextColumn(
                    "Data (GG/MM/AAAA)", required=True
                ),
                "quote": st.column_config.NumberColumn(
                    "Quote", min_value=0.0, format="%.3f", default=0.0
                ),
                "valore_quota": st.column_config.NumberColumn(
                    "Valore Quota (€)",
                    min_value=0.0,
                    format="%.4f €",
                    default=0.0,
                ),
                "importo": st.column_config.NumberColumn(
                    "Importo Versato (€)",
                    min_value=0.0,
                    format="%.2f €",
                    default=0.0,
                ),
            },
            key=editor_key,
        )

        if st.button(
            f"💾 Salva Modifiche per '{selected_invest}' nel JSON", type="primary"
        ):
            records = edited_inv.to_dict(orient="records")
            cleaned_records = []
            for r in records:
                if r.get("data") and str(r["data"]).strip():
                    q = float(r.get("quote") or 0.0)
                    vq = float(r.get("valore_quota") or 0.0)
                    imp = float(r.get("importo") or 0.0)
                    if imp == 0.0 and q > 0 and vq > 0:
                        imp = round(q * vq, 2)

                    cleaned_records.append(
                        {
                            "data": str(r["data"]).strip(),
                            "quote": q,
                            "valore_quota": vq,
                            "importo": imp,
                        }
                    )

            data["investimenti"][selected_invest] = {
                "valore_attuale": float(valore_attuale),
                "movimenti": cleaned_records,
            }
            save_data(data)
            st.success(
                f"Dati di '{selected_invest}' salvati con successo nel JSON!"
            )
            st.rerun()

    else:
        st.info("Nessun investimento trovato nel file JSON.")

# ----------------------------------------------------
# TAB 3: PRESTITI & DEBITI
# ----------------------------------------------------
with tab3:
    st.header("Gestione Prestiti & Debiti")

    prestiti_dict = data.get("prestiti", {})

    if "prestiti" not in data or not isinstance(data["prestiti"], dict):
        data["prestiti"] = {}
        prestiti_dict = data["prestiti"]

    with st.expander(
        "➕ Aggiungi / Crea Nuovo Prestito o Debito",
        expanded=(len(prestiti_dict) == 0),
    ):
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            nuovo_nome = st.text_input(
                "Nome Prestito / Debito", placeholder="es. Prestito Auto"
            )
        with col_c2:
            nuovo_importo = st.number_input(
                "Importo Totale Finanziato (€)",
                min_value=0.0,
                step=100.0,
                value=0.0,
            )
        with col_c3:
            nuove_note = st.text_input(
                "Note / Descrizione", placeholder="es. Tasso fisso, 48 rate"
            )

        if st.button("Crea Prestito", type="primary"):
            if nuovo_nome.strip():
                if nuovo_nome in data["prestiti"]:
                    st.error(f"Un prestito chiamato '{nuovo_nome}' esiste già!")
                else:
                    data["prestiti"][nuovo_nome.strip()] = {
                        "importo_totale": float(nuovo_importo),
                        "note": nuove_note.strip(),
                        "rate": [],
                    }
                    save_data(data)
                    st.success(f"Prestito '{nuovo_nome}' creato con successo!")
                    st.rerun()
            else:
                st.warning("Inserisci un nome valido per il prestito.")

    st.markdown("---")

    if prestiti_dict:
        selected_prestito = st.selectbox(
            "Seleziona Prestito / Debito da visualizzare",
            list(prestiti_dict.keys()),
        )

        prestito_info = prestiti_dict.get(selected_prestito, {})
        importo_totale = float(prestito_info.get("importo_totale", 0.0))
        note_prestito = prestito_info.get("note", "")
        raw_rate = prestito_info.get("rate", [])

        df_base_rate = pd.DataFrame(raw_rate)

        required_cols = [
            "num_rata",
            "data",
            "importo",
            "pagata",
            "debito_residuo",
        ]
        for col in required_cols:
            if col not in df_base_rate.columns:
                if col == "pagata":
                    df_base_rate[col] = False
                elif col in ["importo", "debito_residuo"]:
                    df_base_rate[col] = 0.0
                elif col == "num_rata":
                    df_base_rate[col] = range(1, len(df_base_rate) + 1)
                else:
                    df_base_rate[col] = ""

        editor_key = f"editor_prestito_{selected_prestito}"

        if editor_key in st.session_state:
            edited_data = st.session_state[editor_key]
            df_rate = df_base_rate.copy()

            for row_idx, changes in edited_data.get("edited_rows", {}).items():
                for col, val in changes.items():
                    df_rate.loc[row_idx, col] = val

            for new_row in edited_data.get("added_rows", []):
                df_rate = pd.concat(
                    [df_rate, pd.DataFrame([new_row])], ignore_index=True
                )

            deleted_indices = edited_data.get("deleted_rows", [])
            if deleted_indices:
                df_rate = df_rate.drop(index=deleted_indices).reset_index(
                    drop=True
                )
        else:
            df_rate = df_base_rate.copy()

        df_rate["importo"] = pd.to_numeric(
            df_rate["importo"], errors="coerce"
        ).fillna(0.0)
        df_rate["pagata"] = df_rate["pagata"].astype(bool)

        tot_rimborsato = df_rate[df_rate["pagata"] == True]["importo"].sum()

        if importo_totale <= 0 and not df_rate.empty:
            importo_totale = df_rate["importo"].sum()

        debito_residuo_totale = max(0.0, importo_totale - tot_rimborsato)
        perc_completato = (
            (tot_rimborsato / importo_totale * 100)
            if importo_totale > 0
            else 0.0
        )

        col_p1, col_p2, col_p3, col_p4 = st.columns(4)

        with col_p1:
            st.metric("Importo Totale Finanziato", f"€ {importo_totale:,.2f}")

        with col_p2:
            st.metric("Totale Rimborsato", f"€ {tot_rimborsato:,.2f}")

        with col_p3:
            color_debito = (
                "#EF4444" if debito_residuo_totale > 0 else "#10B981"
            )
            st.markdown(
                f"""
                <div style="text-align: left;">
                    <p style="font-size: 14px; margin-bottom: 4px; color: #9CA3AF; font-family: Source Sans Pro, sans-serif;">Debito Residuo</p>
                    <p style="font-size: 36px; font-weight: 600; margin-top: 0px; margin-bottom: 0px; color: {color_debito}; font-family: Source Sans Pro, sans-serif;">
                        € {debito_residuo_totale:,.2f}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_p4:
            st.metric("Avanzamento Rientro", f"{perc_completato:.1f}%")

        st.progress(min(1.0, max(0.0, perc_completato / 100.0)))
        if note_prestito:
            st.caption(f"📌 **Note:** {note_prestito}")

        st.markdown("---")

        st.subheader(f"Piano di Ammortamento: {selected_prestito}")
        st.caption(
            "Spunta le rate saldate per aggiornare automaticamente il totale rimborsato e il debito residuo."
        )

        edited_rate = st.data_editor(
            df_base_rate[
                ["num_rata", "data", "importo", "pagata", "debito_residuo"]
            ],
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "num_rata": st.column_config.NumberColumn(
                    "N° Rata", step=1, format="%d"
                ),
                "data": st.column_config.TextColumn(
                    "Data Scadenza (GG/MM/AAAA)", required=True
                ),
                "importo": st.column_config.NumberColumn(
                    "Importo Rata (€)",
                    min_value=0.0,
                    format="%.2f €",
                    default=0.0,
                ),
                "pagata": st.column_config.CheckboxColumn(
                    "Pagata", default=False
                ),
                "debito_residuo": st.column_config.NumberColumn(
                    "Debito Residuo Calcolato (€)", format="%.2f €"
                ),
            },
            key=editor_key,
        )

        col_save, col_del = st.columns([4, 1])

        with col_save:
            if st.button(
                f"💾 Salva Piano Rate per '{selected_prestito}'", type="primary"
            ):
                records = edited_rate.to_dict(orient="records")
                cleaned_records = []

                curr_residuo = importo_totale
                for r in records:
                    if r.get("data") and str(r["data"]).strip():
                        imp = float(r.get("importo") or 0.0)
                        is_pagata = bool(r.get("pagata", False))
                        if is_pagata:
                            curr_residuo -= imp

                        cleaned_records.append(
                            {
                                "num_rata": int(
                                    r.get("num_rata") or len(cleaned_records) + 1
                                ),
                                "data": str(r["data"]).strip(),
                                "importo": imp,
                                "pagata": is_pagata,
                                "debito_residuo": round(
                                    max(0.0, curr_residuo), 2
                                ),
                            }
                        )

                data["prestiti"][selected_prestito] = {
                    "importo_totale": float(importo_totale),
                    "note": note_prestito,
                    "rate": cleaned_records,
                }
                save_data(data)
                st.success(
                    f"Piano di ammortamento per '{selected_prestito}' aggiornato e salvato!"
                )
                st.rerun()

        with col_del:
            if st.button(
                f"🗑️ Elimina '{selected_prestito}'", type="secondary"
            ):
                del data["prestiti"][selected_prestito]
                save_data(data)
                st.warning(
                    f"Prestito '{selected_prestito}' eliminato con successo."
                )
                st.rerun()

    else:
        st.info(
            "Nessun prestito o debito presente. Utilizza il pannello qui sopra per aggiungerne uno nuovo!"
        )