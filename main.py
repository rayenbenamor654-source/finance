from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st


TND = Decimal("0.001")


def money(value):
    return Decimal(str(value)).quantize(TND, rounding=ROUND_HALF_UP)


def format_tnd(value):
    """Format dinars with French separators and three decimal places."""
    formatted = f"{money(value):,.3f}"
    return formatted.replace(",", " ").replace(".", ",") + " TND"


def simple_interest(capital, annual_rate_percent, duration, unit):
    """Calculate simple interest using a 360-day commercial year."""
    capital = Decimal(str(capital))
    rate = Decimal(str(annual_rate_percent)) / Decimal("100")
    duration = Decimal(str(duration))
    if unit == "Jours" and duration != duration.to_integral_value():
        raise ValueError("La durée en jours doit être un nombre entier.")
    year_fraction = {
        "Années": duration,
        "Mois": duration / Decimal("12"),
        "Jours": duration / Decimal("360"),
    }[unit]
    interest = money(capital * rate * year_fraction)
    return interest, money(capital + interest), year_fraction


def value_date(operation_date, operation_type):
    """Apply the requested +/- 7-day value date to a savings operation."""
    if operation_type == "Versement":
        return operation_date + timedelta(days=7)
    if operation_type == "Retrait":
        return operation_date - timedelta(days=7)
    raise ValueError("Type d'opération invalide.")


def days_360(start, end):
    """Return the number of days using a 30/360 commercial calendar."""
    return (
        (end.year - start.year) * 360
        + (end.month - start.month) * 30
        + min(end.day, 30)
        - min(start.day, 30)
    )


def calculate_savings(initial_balance, annual_rate, operations, year):
    """Estimate annual simple interest using the operation value dates."""
    balance = Decimal(str(initial_balance))
    rate = Decimal(str(annual_rate))
    start, end = date(year, 1, 1), date(year + 1, 1, 1)
    valued_operations, segments = [], []

    for operation_date, operation_type, amount, *_ in operations:
        amount = Decimal(str(amount))
        signed_amount = amount if operation_type == "Versement" else -amount
        valued_operations.append(
            (value_date(operation_date, operation_type), operation_date, operation_type, signed_amount)
        )

    valued_operations.sort(key=lambda item: (item[0], item[1], item[2]))
    segment_start = start
    for value, operation_date, _, signed_amount in valued_operations:
        value = max(value, start)
        if value >= end:
            continue
        days = days_360(segment_start, value)
        if days > 0:
            number = balance * Decimal(days) / Decimal("100")
            segments.append((segment_start, value, balance, days, number))
        balance += signed_amount
        if balance < 0:
            raise ValueError(
                f"Le retrait du {operation_date.strftime('%d/%m/%Y')} dépasse le solde disponible."
            )
        segment_start = value

    days = days_360(segment_start, end)
    if days > 0:
        number = balance * Decimal(days) / Decimal("100")
        segments.append((segment_start, end, balance, days, number))

    total_numbers = sum((segment[4] for segment in segments), Decimal("0"))
    if rate <= 0:
        raise ValueError("Le taux annuel doit être supérieur à zéro.")
    divisor = Decimal("360") / rate
    interest = money(total_numbers / divisor)
    return {
        "balance": balance,
        "interest": interest,
        "capital": money(balance + interest),
        "total_numbers": total_numbers,
        "divisor": divisor,
        "segments": segments,
    }


def build_ledger(initial_balance, operations):
    """Build chronological rows and reject transactions that overdraw the account."""
    balance = Decimal(str(initial_balance))
    rows = []
    ordered_operations = sorted(
        enumerate(operations), key=lambda entry: (entry[1][0], entry[0])
    )
    for _, (operation_date, operation_type, description, amount) in ordered_operations:
        amount = Decimal(str(amount))
        signed_amount = amount if operation_type == "Versement" else -amount
        next_balance = balance + signed_amount
        if next_balance < 0:
            raise ValueError(
                f"Retrait refusé le {operation_date.strftime('%d/%m/%Y')} : "
                f"solde disponible {format_tnd(balance)}, retrait demandé {format_tnd(amount)}."
            )
        balance = next_balance
        rows.append({
            "Date d’opération": operation_date.strftime("%d/%m/%Y"),
            "Date de valeur": value_date(operation_date, operation_type).strftime("%d/%m/%Y"),
            "Description": description,
            "Type": operation_type,
            "Montant (TND)": format_tnd(amount),
            "Solde (TND)": format_tnd(balance),
        })
    return rows, balance


# ---------- App setup and visual style ----------
st.set_page_config(
    page_title="Finance | Tableau de bord",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
      :root { color-scheme:light; --ink:#172033; --muted:#667085; --violet:#7357d9; --violet-dark:#5b43b5; --line:#e8e3d8; --surface:#fff; --coral:#ef766a; }
      html,body,[class*="css"] { font-family:'DM Sans',sans-serif; }
      .stApp,[data-testid="stAppViewContainer"] { background:linear-gradient(135deg,#f8f6ef 0%,#f2f7f5 55%,#f7f1fa 100%); color:var(--ink); }
      [data-testid="stHeader"] { background:rgba(248,246,239,.92); }
      [data-testid="stSidebar"] { background:linear-gradient(180deg,#087e72 0%,#22a99a 100%); border-right:1px solid #087266; }
      [data-testid="stSidebar"] * { color:#fff !important; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#e2f7f3 !important; }
      [data-testid="stSidebar"] hr { border-color:rgba(255,255,255,.28); }
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color:#d8f3ef !important; }
      h1,h2,h3 { font-family:'Manrope',sans-serif; color:var(--ink); letter-spacing:-.035em; }
      .stMainBlockContainer { padding-top:2rem; }
      .estimate-heading { margin:0 0 1rem; padding-left:.75rem; border-left:4px solid var(--coral); font-size:1.6rem; font-weight:800; line-height:1.25; }
      .hero { position:relative; overflow:hidden; padding:1.8rem 2rem; border-radius:20px; margin:.15rem 0 1.7rem; color:#fff; background:linear-gradient(118deg,#087e72 0%,#159889 55%,#22a99a 100%); box-shadow:0 14px 34px rgba(8,126,114,.18); }
      .hero h1 { color:#fff; margin:0 0 .4rem; font-size:2rem; } .hero p { color:#e9fffb; margin:0; font-size:1rem; }
      .eyebrow { text-transform:uppercase; letter-spacing:.15em; color:#bff3e9; font-weight:800; font-size:.72rem; margin-bottom:.5rem; }
      .section-card { background:var(--surface); color:var(--ink); border:1px solid var(--line); border-radius:16px; padding:1.2rem 1.35rem; margin-bottom:1rem; }
      [data-testid="stVerticalBlockBorderWrapper"] { background:var(--surface); border:1px solid var(--line); border-radius:16px; }
      [data-testid="stMetric"] { background:linear-gradient(145deg,#fff 0%,#f7f5ff 100%); border:1px solid #ddd6f5; border-radius:15px; padding:1.05rem 1.2rem; }
      [data-testid="stMetricLabel"] { color:#656d82; font-weight:700; } [data-testid="stMetricValue"] { color:var(--violet); font-family:'Manrope',sans-serif; }
      div.stButton>button[kind="primary"],div[data-testid="stFormSubmitButton"] button[kind="primary"] { background:var(--violet); border:0; border-radius:10px; color:#fff; }
      div.stButton>button[kind="primary"]:hover,div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover { background:var(--violet-dark); }
      div[data-testid="stNumberInput"] input,div[data-testid="stDateInput"] input,div[data-testid="stSelectbox"] [role="combobox"],div[data-testid="stTextInput"] input { color:var(--ink); background:#fff; border:1px solid #dcd7e8; border-radius:9px; }
      [data-testid="stWidgetLabel"],[data-testid="stMarkdownContainer"] { color:var(--ink); } [data-testid="stCaptionContainer"] { color:var(--muted); }
      .small-note { color:var(--muted); font-size:.87rem; }
      [data-testid="stDataFrame"] { border:1px solid #dfd8f1; border-radius:12px; overflow:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## ◈ FINANCE")
    st.markdown("Votre espace de calcul financier")
    st.markdown("---")
    st.markdown("**ESPACE DE TRAVAIL**")
    page = st.radio(
        "Navigation",
        ["1 · Calcul d’intérêt", "2 · Compte d’épargne"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Calculs indicatifs · Vérifiez les conditions de votre établissement.")


# ---------- Page 1: simple interest ----------
if page == "1 · Calcul d’intérêt":
    st.markdown(
        "<div class='hero'><div class='eyebrow'>ESPACE FINANCE &nbsp; / &nbsp; 01</div>"
        "<h1>Calcul d’intérêt simple</h1>"
        "<p>Une estimation claire du rendement de votre capital, selon la durée choisie.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown("### Simulateur de rendement")
    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            capital = c1.number_input("Capital initial (TND)", min_value=0.0, value=0.0, step=100.0)
            annual_rate = c2.number_input("Taux annuel (%)", min_value=0.0, value=5.0, step=0.25)
            c3, c4 = st.columns(2)
            unit = c4.selectbox("Unité de durée", ["Années", "Mois", "Jours"])
            if unit == "Jours":
                duration = c3.number_input("Durée", min_value=0, value=2, step=1, format="%d", key="duration_days")
            else:
                duration = c3.number_input("Durée", min_value=0.0, value=2.0, step=0.5, key=f"duration_{unit}")
            st.markdown(
                "<p class='small-note'>Base de calcul : année commerciale de 360 jours pour une durée en jours.</p>",
                unsafe_allow_html=True,
            )
            calculate_simple = st.button("Calculer l’intérêt simple", type="primary")

    if calculate_simple:
        try:
            st.session_state.simple_interest_result = (
                simple_interest(capital, annual_rate, duration, unit) if duration > 0 else None
            )
        except ValueError as error:
            st.session_state.simple_interest_result = None
            st.error(str(error))
    with right:
        result = st.session_state.get("simple_interest_result")
        if result:
            interest, final_capital, _ = result
            st.markdown("<h2 class='estimate-heading'>Votre estimation</h2>", unsafe_allow_html=True)
            st.metric("Intérêts générés", format_tnd(interest))
            st.metric("Capital final estimé", format_tnd(final_capital))
        else:
            st.info("Complétez les paramètres puis cliquez sur « Calculer l’intérêt simple ».")

    with st.expander("À propos de la méthode"):
        st.write(
            "Les intérêts simples sont calculés uniquement sur le capital initial : "
            "**I = C × t × n**, où C est le capital, t le taux annuel sous forme décimale "
            "et n la durée exprimée en années. Les intérêts ne sont pas capitalisés."
        )


# ---------- Page 2: savings account ----------
else:
    st.markdown(
        "<div class='hero'><div class='eyebrow'>ESPACE FINANCE &nbsp; / &nbsp; 02</div>"
        "<h1>Compte d’épargne</h1>"
        "<p>Suivez les opérations de votre compte et le solde disponible.</p></div>",
        unsafe_allow_html=True,
    )

    account_key = "savings_account"
    operations_key = "savings_ledger_operations"
    if not st.session_state.get("savings_account_started", False):
        st.markdown("### Démarrer un compte d’épargne")
        with st.form("start_savings_account_form"):
            c1, c2, c3, c4 = st.columns(4)
            start_date = c1.date_input("Date de début", value=date.today())
            initial = c2.number_input("Capital initial (TND)", min_value=0.0, value=0.0, step=100.0)
            annual_rate = c3.number_input("Taux d’intérêt (%)", min_value=0.0, value=5.0, step=0.25)
            capitalization_duration = c4.selectbox(
                "Durée de capitalisation", ["3 mois", "6 mois", "1 an"]
            )
            start_account = st.form_submit_button("Démarrer le compte épargne", type="primary")

        if start_account:
            st.session_state[account_key] = {
                "date": start_date,
                "initial": initial,
                "rate": annual_rate,
                "capitalization_duration": capitalization_duration,
            }
            st.session_state[operations_key] = []
            st.session_state.savings_account_started = True
            st.rerun()
        st.info("Renseignez les paramètres du compte, puis cliquez sur « Démarrer le compte épargne ».")
        st.stop()

    account = st.session_state[account_key]
    start_date = account["date"]
    initial = account["initial"]
    annual_rate = account["rate"]
    operations = st.session_state.get(operations_key, [])

    st.markdown("### Vue d’ensemble du compte")
    info1, info2, info3, info4 = st.columns(4)
    info1.metric("Date de début", start_date.strftime("%d/%m/%Y"))
    info2.metric("Capital initial", format_tnd(initial))
    info3.metric("Taux d’intérêt", f"{annual_rate:.2f} %")
    info4.metric("Durée de capitalisation", account["capitalization_duration"])

    if st.button("Fermer le compte et recommencer"):
        st.session_state.savings_account_started = False
        st.session_state.pop(account_key, None)
        st.session_state.pop(operations_key, None)
        st.rerun()

    st.markdown("### Ajouter une opération")
    with st.form("savings_operation_form", clear_on_submit=True):
        op1, op2, op3, op4 = st.columns([1, 1, 1.5, 1])
        operation_date = op1.date_input(
            "Date d’opération",
            value=max(start_date, date.today()),
            min_value=start_date,
            key="savings_operation_date",
        )
        operation_type = op2.selectbox("Type", ["Versement", "Retrait"])
        description = op3.text_input("Description", placeholder="Ex. Dépôt initial")
        amount = op4.number_input("Montant (TND)", min_value=0.001, value=100.0, step=50.0)
        add_operation = st.form_submit_button("Ajouter à l’historique", type="primary")

    if add_operation:
        if not description.strip():
            st.error("Veuillez saisir une description pour l’opération.")
        else:
            new_operation = (operation_date, operation_type, description.strip(), amount)
            candidate_operations = operations + [new_operation]
            try:
                build_ledger(initial, candidate_operations)
                st.session_state[operations_key] = candidate_operations
                st.success("Opération ajoutée au compte.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    try:
        ledger_rows, current_balance = build_ledger(initial, operations)
        st.markdown("### Historique du compte")
        st.metric("Solde disponible", format_tnd(current_balance))
        if ledger_rows:
            st.dataframe(ledger_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune opération pour le moment. Le solde initial est de " + format_tnd(initial) + ".")

        st.markdown("### Synthèse annuelle des intérêts")
        year = start_date.year
        interest_operations = [
            (op_date, op_type, amount, description)
            for op_date, op_type, description, amount in operations
        ]
        result = calculate_savings(initial, annual_rate, interest_operations, year)
        m1, m2, m3 = st.columns(3)
        m1.metric("Solde hors intérêts", format_tnd(result["balance"]))
        m2.metric("Intérêts estimés", format_tnd(result["interest"]))
        m3.metric("Capital acquis", format_tnd(result["capital"]))

        st.markdown("### Détail du calcul des intérêts")
        rows = [
            {
                "Du": start.strftime("%d/%m/%Y"),
                "Au": end.strftime("%d/%m/%Y"),
                "Solde (TND)": float(money(balance)),
                "Jours (30/360)": days,
                "Nombres": float(money(number)),
            }
            for start, end, balance, days, number in result["segments"]
        ]
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        summary1, summary2 = st.columns(2)
        summary1.markdown(f"**Total des nombres :** {money(result['total_numbers']):,.2f}")
        summary2.markdown(f"**Diviseur :** {result['divisor']:,.4f}")
    except ValueError as error:
        st.error(str(error))
