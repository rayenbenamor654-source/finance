from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st


TND = Decimal("0.001")
DAYS_PER_YEAR = Decimal("360")
DEFAULT_WITHHOLDING_TAX_PERCENT = Decimal("20")


def money(value):
    return Decimal(str(value)).quantize(TND, rounding=ROUND_HALF_UP)


def format_tnd(value):
    formatted = f"{money(value):,.3f}"
    return formatted.replace(",", " ").replace(".", ",") + " TND"


def simple_interest(capital, annual_rate_percent, duration, unit):
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


def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def value_date(operation_date, operation_type):
    if operation_type == "Versement":
        return operation_date + timedelta(days=7)
    if operation_type == "Retrait":
        return operation_date - timedelta(days=7)
    raise ValueError("Type d'opération invalide.")


def build_ledger(
    initial_balance,
    operations,
    start_date,
    annual_rate,
    capitalization_months,
    withholding_tax_percent=DEFAULT_WITHHOLDING_TAX_PERCENT,
):
    """Build the ledger with actual-day, 30/360 simple interest by capitalization period."""
    balance = money(initial_balance)
    annual_rate = Decimal(str(annual_rate)) / Decimal("100")
    withholding_rate = Decimal(str(withholding_tax_percent)) / Decimal("100")

    transaction_events = []
    for index, (operation_date, operation_type, amount) in enumerate(operations):
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Le montant d'une opération doit être supérieur à zéro.")
        raw_value_date = value_date(operation_date, operation_type)
        effective_date = max(raw_value_date, start_date)
        signed_amount = amount if operation_type == "Versement" else -amount
        transaction_events.append(
            (effective_date, 1, index, operation_date, raw_value_date, operation_type, amount, signed_amount)
        )

    last_event_date = max((event[0] for event in transaction_events), default=start_date)
    events = [
        (event[0], event[1], event[2], "operation", event)
        for event in transaction_events
    ]

    # Derive boundaries from the account start date and selected duration. Only
    # completed periods through the last value date are capitalized; later
    # operations remain in the open period until its actual boundary.
    period_number = 1
    capitalization_date = add_months(start_date, capitalization_months * period_number)
    while capitalization_date <= last_event_date:
        events.append((capitalization_date, 0, period_number, "capitalization", None))
        period_number += 1
        capitalization_date = add_months(start_date, capitalization_months * period_number)

    events.sort(key=lambda event: (event[0], event[1], event[2]))
    rows = [{
        "Date d’opération": start_date.strftime("%d/%m/%Y"),
        "Date de valeur": start_date.strftime("%d/%m/%Y"),
        "Type": "Ouverture",
        "Montant (TND)": format_tnd(balance),
        "Intérêts bruts (TND)": "—",
        "Retenue fiscale (TND)": "—",
        "Solde (TND)": format_tnd(balance),
    }]

    cursor = start_date
    accrued_interest = Decimal("0")
    for event_date, _, _, event_type, payload in events:
        elapsed_days = (event_date - cursor).days
        if elapsed_days > 0:
            accrued_interest += (
                balance * Decimal(elapsed_days) * annual_rate / DAYS_PER_YEAR
            )
            cursor = event_date

        if event_type == "capitalization":
            gross_interest = money(accrued_interest)
            tax = money(gross_interest * withholding_rate)
            net_interest = money(gross_interest - tax)
            balance = money(balance + net_interest)
            rows.append({
                "Date d’opération": event_date.strftime("%d/%m/%Y"),
                "Date de valeur": event_date.strftime("%d/%m/%Y"),
                "Type": "Capitalisation",
                "Montant (TND)": format_tnd(net_interest),
                "Intérêts bruts (TND)": format_tnd(gross_interest),
                "Retenue fiscale (TND)": format_tnd(tax),
                "Solde (TND)": format_tnd(balance),
            })
            accrued_interest = Decimal("0")
            continue

        _, _, _, operation_date, raw_value_date, operation_type, amount, signed_amount = payload
        next_balance = balance + signed_amount
        if next_balance < 0:
            raise ValueError(
                f"Retrait refusé le {operation_date.strftime('%d/%m/%Y')} : "
                f"solde disponible {format_tnd(balance)}, retrait demandé {format_tnd(amount)}."
            )
        balance = money(next_balance)
        rows.append({
            "Date d’opération": operation_date.strftime("%d/%m/%Y"),
            "Date de valeur": max(raw_value_date, start_date).strftime("%d/%m/%Y"),
            "Type": operation_type,
            "Montant (TND)": format_tnd(amount),
            "Intérêts bruts (TND)": "—",
            "Retenue fiscale (TND)": "—",
            "Solde (TND)": format_tnd(balance),
        })

    return rows, balance, money(accrued_interest)


st.set_page_config(
    page_title="Finance | Tableau de bord",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
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
h1,h2,h3 { font-family:'Manrope',sans-serif; color:var(--ink); letter-spacing:-.035em; }
.stMainBlockContainer { padding-top:2rem; }
.hero { padding:1.8rem 2rem; border-radius:20px; margin:.15rem 0 1.7rem; color:#fff; background:linear-gradient(118deg,#087e72 0%,#159889 55%,#22a99a 100%); }
.hero h1 { color:#fff; margin:0 0 .4rem; font-size:2rem; }
.hero p { color:#e9fffb; margin:0; }
.eyebrow { text-transform:uppercase; letter-spacing:.15em; color:#bff3e9; font-weight:800; font-size:.72rem; margin-bottom:.5rem; }
[data-testid="stMetric"] { background:linear-gradient(145deg,#fff 0%,#f7f5ff 100%); border:1px solid #ddd6f5; border-radius:15px; padding:1.05rem 1.2rem; }
[data-testid="stMetricValue"] { color:var(--violet); font-family:'Manrope',sans-serif; }
div.stButton>button[kind="primary"],div[data-testid="stFormSubmitButton"] button[kind="primary"] { background:var(--violet); border:0; border-radius:10px; color:#fff; }
div.stButton>button[kind="primary"]:hover,div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover { background:var(--violet-dark); }
</style>
""", unsafe_allow_html=True)

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


if page == "1 · Calcul d’intérêt":
    st.markdown(
        "<div class='hero'><div class='eyebrow'>ESPACE FINANCE &nbsp; / &nbsp; 01</div>"
        "<h1>Calcul d’intérêt simple</h1><p>Une estimation claire du rendement de votre capital, selon la durée choisie.</p></div>",
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
            st.markdown("### Votre estimation")
            st.metric("Intérêts générés", format_tnd(interest))
            st.metric("Capital final estimé", format_tnd(final_capital))
        else:
            st.info("Complétez les paramètres puis cliquez sur « Calculer l’intérêt simple ».")

    with st.expander("À propos de la méthode"):
        st.write(
            "Les intérêts simples sont calculés uniquement sur le capital initial : **I = C × t × n**, "
            "où C est le capital, t le taux annuel sous forme décimale et n la durée exprimée en années."
        )

else:
    st.markdown(
        "<div class='hero'><div class='eyebrow'>ESPACE FINANCE &nbsp; / &nbsp; 02</div>"
        "<h1>Compte d’épargne</h1><p>Suivez les opérations, les intérêts capitalisés et le solde disponible.</p></div>",
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
            annual_rate = c3.number_input("Taux d’intérêt annuel (%)", min_value=0.0, value=5.0, step=0.25)
            capitalization_duration = c4.selectbox("Durée de capitalisation", ["1 mois", "3 mois", "6 mois", "1 an"])
            apply_tax = st.checkbox("Appliquer la retenue fiscale de 20 %", value=True)
            start_account = st.form_submit_button("Démarrer le compte épargne", type="primary")

        if start_account:
            st.session_state[account_key] = {
                "date": start_date,
                "initial": initial,
                "rate": annual_rate,
                "capitalization_duration": capitalization_duration,
                "withholding_tax_percent": 20 if apply_tax else 0,
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
    withholding_tax_percent = account.get("withholding_tax_percent", 20)
    operations = st.session_state.get(operations_key, [])
    capitalization_months = {"1 mois": 1, "3 mois": 3, "6 mois": 6, "1 an": 12}[account["capitalization_duration"]]

    st.markdown("### Vue d’ensemble du compte")
    info1, info2, info3, info4 = st.columns(4)
    info1.metric("Date de début", start_date.strftime("%d/%m/%Y"))
    info2.metric("Capital initial", format_tnd(initial))
    info3.metric("Taux d’intérêt", f"{annual_rate:.2f} %")
    info4.metric("Durée de capitalisation", account["capitalization_duration"])
    if withholding_tax_percent:
        st.caption(f"Retenue fiscale appliquée à chaque capitalisation : {withholding_tax_percent:.0f} % des intérêts bruts.")
    else:
        st.caption("Aucune retenue fiscale n’est appliquée aux intérêts.")

    if st.button("Fermer le compte et recommencer"):
        st.session_state.savings_account_started = False
        st.session_state.pop(account_key, None)
        st.session_state.pop(operations_key, None)
        st.rerun()

    st.markdown("### Ajouter une opération")
    last_operation_date = max((operation[0] for operation in operations), default=start_date)
    minimum_operation_date = max(start_date, last_operation_date)
    with st.form("savings_operation_form", clear_on_submit=True):
        op1, op2, op3 = st.columns([1, 1, 1])
        operation_date = op1.date_input(
            "Date d’opération",
            value=max(minimum_operation_date, date.today()),
            min_value=minimum_operation_date,
        )
        operation_type = op2.selectbox("Type", ["Versement", "Retrait"])
        amount = op3.number_input("Montant (TND)", min_value=0.001, value=100.0, step=50.0)
        add_operation = st.form_submit_button("Ajouter à l’historique", type="primary")

    if add_operation:
        candidate_operations = operations + [(operation_date, operation_type, amount)]
        try:
            build_ledger(
                initial, candidate_operations, start_date, annual_rate,
                capitalization_months, withholding_tax_percent,
            )
            st.session_state[operations_key] = candidate_operations
            st.success("Opération ajoutée au compte.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

    try:
        ledger_rows, current_balance, pending_interest = build_ledger(
            initial, operations, start_date, annual_rate,
            capitalization_months, withholding_tax_percent,
        )
        st.markdown("### Historique du compte")
        balance_col, pending_col = st.columns(2)
        balance_col.metric("Solde disponible", format_tnd(current_balance))
        pending_col.metric("Intérêts bruts en attente", format_tnd(pending_interest))
        st.caption(
            f"Les intérêts sont calculés par tranches de jours (base 360) et crédités tous les "
            f"{capitalization_months} mois. Les opérations après la dernière capitalisation restent "
            "dans la période en cours ; les intérêts affichés comme en attente ne sont pas encore crédités."
        )
        st.dataframe(ledger_rows, use_container_width=True, hide_index=True)
    except ValueError as error:
        st.error(str(error))
