from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st


TND = Decimal("0.001")


def money(value):
    return Decimal(str(value)).quantize(TND, rounding=ROUND_HALF_UP)


def format_tnd(value):
    formatted = f"{money(value):,.3f}"
    return formatted.replace(" ", "").replace(",", " ").replace(".", ",") + " TND"


def simple_interest(capital, annual_rate_percent, duration, unit):
    capital = Decimal(str(capital))
    rate = Decimal(str(annual_rate_percent)) / Decimal("100")
    duration = Decimal(str(duration))
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
    if operation_type not in ("Versement", "Retrait"):
        raise ValueError("Type d’opération invalide.")

    if operation_type == "Versement":
        if operation_date.day in (1, 16):
            return operation_date
        if operation_date.day < 16:
            return date(operation_date.year, operation_date.month, 16)
        return add_months(operation_date.replace(day=1), 1)

    if operation_date.day <= 15:
        return operation_date.replace(day=1)
    return date(operation_date.year, operation_date.month, 16)


def days_360(start, end):
    return (
        (end.year - start.year) * 360
        + (end.month - start.month) * 30
        + min(end.day, 30)
        - min(start.day, 30)
    )


def calculate_savings(initial_balance, annual_rate, operations, opening_date, frequency_months):
    balance = money(initial_balance)
    rate = Decimal(str(annual_rate))

    if balance < 0:
        raise ValueError("Le capital initial ne peut pas être négatif.")
    if rate <= 0:
        raise ValueError("Le taux annuel doit être supérieur à zéro.")
    if frequency_months not in (3, 6):
        raise ValueError("Choisissez une capitalisation trimestrielle ou semestrielle.")

    end = add_months(opening_date, 12)
    valued_operations = []

    for operation_date, operation_type, amount in operations:
        amount = money(amount)
        if amount <= 0:
            raise ValueError("Le montant d’une opération doit être supérieur à zéro.")
        if not opening_date <= operation_date < end:
            continue

        effective_date = max(value_date(operation_date, operation_type), opening_date)
        if effective_date >= end:
            continue

        signed_amount = amount if operation_type == "Versement" else -amount
        valued_operations.append((effective_date, operation_date, operation_type, signed_amount))

    valued_operations.sort(key=lambda item: (item[0], item[1], item[2]))
    divisor = Decimal("360") / rate
    segments = []
    pending_segments = []
    statement_rows = [{
        "Date d’opération": opening_date.strftime("%d/%m/%Y"),
        "Date de valeur": opening_date.strftime("%d/%m/%Y"),
        "Mouvement": "Ouverture du compte",
        "Montant (TND)": float(balance),
        "Solde après mouvement (TND)": float(balance),
    }]
    cursor = opening_date
    next_boundary = add_months(opening_date, frequency_months)
    pending_interest = Decimal("0")
    total_interest = Decimal("0")
    boundary_passed = False

    def accrue(until):
        nonlocal pending_interest, cursor
        days = days_360(cursor, until)
        if days > 0:
            number = balance * Decimal(days) / Decimal("100")
            interest = number / divisor
            pending_interest += interest
            pending_segments.append((cursor, until, balance, days, number))
        cursor = until

    def apply_operation(operation):
        nonlocal balance
        effective_date, operation_date, operation_type, signed_amount = operation
        balance = money(balance + signed_amount)
        if balance < 0:
            raise ValueError(
                f"Le retrait du {operation_date.strftime('%d/%m/%Y')} dépasse le solde disponible "
                f"à sa date de valeur ({effective_date.strftime('%d/%m/%Y')})."
            )
        statement_rows.append({
            "Date d’opération": operation_date.strftime("%d/%m/%Y"),
            "Date de valeur": effective_date.strftime("%d/%m/%Y"),
            "Mouvement": operation_type,
            "Montant (TND)": float(signed_amount),
            "Solde après mouvement (TND)": float(balance),
        })

    for operation in valued_operations:
        effective_date = operation[0]

        while next_boundary < effective_date:
            accrue(next_boundary)
            boundary_passed = True
            elapsed_months = (
                (next_boundary.year - opening_date.year) * 12
                + next_boundary.month - opening_date.month
            )
            next_boundary = add_months(
                opening_date,
                (elapsed_months // frequency_months + 1) * frequency_months,
            )

        if boundary_passed and effective_date > cursor and pending_interest > 0:
            credited_interest = money(pending_interest)
            balance = money(balance + credited_interest)
            total_interest += credited_interest
            statement_rows.append({
                "Date d’opération": "—",
                "Date de valeur": effective_date.strftime("%d/%m/%Y"),
                "Mouvement": "Capitalisation des intérêts",
                "Montant (TND)": float(credited_interest),
                "Solde après mouvement (TND)": float(balance),
            })
            segments.extend(pending_segments)
            pending_segments.clear()
            pending_interest = Decimal("0")
            boundary_passed = False

        accrue(effective_date)
        apply_operation(operation)

    accrue(end)

    return {
        "balance": balance,
        "interest": money(total_interest),
        "capital": balance,
        "segments": segments,
        "statement": statement_rows,
        "end_date": end,
    }


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
      :root {
        --ink: #20354a; --muted: #718096; --teal: #167c70; --teal-dark: #11675e;
        --canvas: #f2f0e9; --surface: #faf9f5; --line: #e4e0d5; --gold: #c49a53;
        --soft-teal: #e4f3ef; --soft-gold: #f6edda;
      }
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
      .stApp { background: var(--canvas); color: var(--ink); }
      [data-testid="stHeader"] { background: rgba(242, 240, 233, .92); backdrop-filter: blur(10px); }
      [data-testid="stSidebar"] { background: linear-gradient(180deg, #20384b 0%, #172d3e 100%); border-right: 1px solid #304a5c; }
      [data-testid="stSidebar"] * { color: #f2f0e9 !important; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c2d0d5 !important; }
      [data-testid="stSidebar"] hr { border-color: #496070; }
      [data-testid="stSidebar"] [role="radiogroup"] label { background: transparent; border-radius: 10px; padding: 7px 10px; margin: 3px 0; }
      [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background: rgba(79, 195, 168, .16); }
      h1, h2, h3 { font-family: 'Manrope', sans-serif; color: var(--ink); letter-spacing: -.035em; }
      h2 { font-size: 1.55rem; margin-top: .5rem; }
      h3 { font-size: 1.22rem; }
      .stMainBlockContainer { padding-top: 2rem; }
      .hero {
        position: relative; overflow: hidden; padding: 2.1rem 2.2rem; border-radius: 22px;
        margin: .15rem 0 1.7rem; color: #f7f5ef;
        background: linear-gradient(118deg, #20384b 0%, #27665f 70%, #3a8577 100%);
        box-shadow: 0 16px 36px rgba(32, 56, 75, .16);
        animation: hero-enter .5s ease-out both;
      }
      .hero::after {
        content: ''; position: absolute; width: 230px; height: 230px; border-radius: 50%;
        right: -75px; top: -135px; border: 1px solid rgba(242,240,233,.17);
        box-shadow: 0 0 0 25px rgba(242,240,233,.035), 0 0 0 52px rgba(242,240,233,.025);
      }
      .hero h1 { color: #f7f5ef; margin: 0 0 .45rem; font-size: 2.35rem; font-weight: 800; }
      .hero p { color: #dfe9e4; margin: 0; font-size: 1.02rem; }
      .eyebrow { text-transform: uppercase; letter-spacing: .18em; color: #efd78f;
                 font-weight: 800; font-size: .76rem; margin-bottom: .55rem; }
      .section-card { background: linear-gradient(135deg, var(--surface), #edf5f2); border: 1px solid #d5e5df;
                      border-radius: 16px; padding: 1.35rem 1.5rem; margin-bottom: 1rem; }
      .estimation-panel {
        background: linear-gradient(145deg, #faf9f5 0%, #edf7f3 100%);
        border: 1px solid #d1e5de; border-radius: 20px; padding: 1.35rem;
        box-shadow: 0 12px 28px rgba(32, 56, 75, .09);
      }
      .estimation-panel h3 { margin: 0 0 1rem; font-size: 1.35rem; }
      [data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px; transition: box-shadow .2s ease, transform .2s ease; }
      [data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow: 0 10px 24px rgba(32,56,75,.08); transform: translateY(-1px); }
      [data-testid="stMetric"] { background: linear-gradient(145deg, #ffffff 0%, var(--soft-teal) 100%); border: 1px solid #d5e7e1;
        border-radius: 15px; padding: 1.15rem 1.25rem; animation: metric-enter .45s ease both;
        box-shadow: 0 8px 18px rgba(22, 124, 112, .07); }
      [data-testid="stMetricLabel"] { color: #5d7280; font-weight: 700; font-size: .95rem; }
      [data-testid="stMetricValue"] { color: var(--teal); font-family: 'Manrope', sans-serif; font-size: 1.75rem; }
      div.stButton > button[kind="primary"] { background: linear-gradient(135deg, var(--teal), #239585); border: 0;
        border-radius: 11px; padding: .55rem 1.1rem; font-weight: 700; box-shadow: 0 7px 16px rgba(22,124,112,.16); }
      div.stButton > button[kind="primary"]:hover { background: var(--teal-dark); transform: translateY(-1px); }
      [data-testid="stForm"] { background: linear-gradient(145deg, #ffffff 0%, #f1f7f4 100%); border: 1px solid #d8e5df;
        border-radius: 18px; padding: 1.1rem 1.25rem; box-shadow: 0 10px 24px rgba(32,56,75,.06); }
      [data-testid="stForm"] label { color: #4e6573; font-weight: 700; }
      [data-testid="stDataFrame"] { border: 1px solid #dde4e8; border-radius: 14px; overflow: hidden;
        box-shadow: 0 8px 20px rgba(32,56,75,.05); }
      [data-testid="stExpander"] { border: 1px solid #e1dfd4; border-radius: 14px; background: var(--surface); }
      .small-note { color: var(--muted); font-size: .92rem; }
      .stSuccess { border-radius: 12px; background: #e8f5ef; }
      @keyframes hero-enter { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      @keyframes metric-enter { from { opacity: 0; transform: translateY(7px); } to { opacity: 1; transform: translateY(0); } }
      @media (max-width: 640px) {
        .hero { padding: 1.6rem 1.35rem; }
        .hero h1 { font-size: 1.75rem; }
        h2 { font-size: 1.35rem; }
      }
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## ◈ FINANCE")
    st.markdown("**Votre espace de calcul financier**")
    st.markdown("---")
    st.markdown("**ESPACE DE TRAVAIL**")
    page = st.radio("Navigation", ["1 · Calcul d’intérêt", "2 · Compte d’épargne"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("Estimations indicatives · Consultez les conditions de votre établissement.")


if page == "1 · Calcul d’intérêt":
    st.markdown(
        "<div class='hero'><div class='eyebrow'>ESPACE FINANCE &nbsp; / &nbsp; 01</div>"
        "<h1>Calcul d’intérêt simple</h1>"
        "<p>Estimez la rémunération de votre capital, sans capitalisation des intérêts.</p></div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            capital = c1.number_input("Capital initial (TND)", min_value=0.0, value=0.0, step=100.0)
            annual_rate = c2.number_input("Taux annuel (%)", min_value=0.0, value=5.0, step=0.25)
            c3, c4 = st.columns(2)
            duration = c3.number_input("Durée", min_value=0.0, value=2.0, step=0.5)
            unit = c4.selectbox("Période", ["Années", "Mois", "Jours"])

    with right:
        if duration > 0:
            interest, final_capital, _ = simple_interest(capital, annual_rate, duration, unit)
            with st.container():
                st.markdown('<div class="estimation-panel">', unsafe_allow_html=True)
                st.markdown("### Votre estimation")
                st.metric("Intérêts estimés", format_tnd(interest))
                st.metric("Capital final", format_tnd(final_capital))
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Indiquez une durée supérieure à zéro pour afficher l’estimation.")

    with st.expander("À propos du calcul"):
        st.write(
            "Les intérêts simples sont calculés uniquement sur le capital initial et ne sont pas ajoutés au capital "
            "pendant la période choisie. Pour les durées en jours, le calcul utilise une année commerciale de 360 jours."
        )

else:
    st.markdown(
        "<div class='hero'><div class='eyebrow'>ESPACE FINANCE &nbsp; / &nbsp; 02</div>"
        "<h1>Compte d’épargne</h1>"
        "<p>Suivez vos versements et retraits, avec des intérêts capitalisés selon la période choisie.</p></div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    opening_date = c1.date_input("Date d’ouverture du compte", value=date.today())
    initial = c2.number_input("Capital initial (TND)", min_value=0.0, value=0.0, step=100.0)
    rate = c3.number_input("Taux annuel (%)", min_value=0.01, value=5.0, step=0.25)
    frequency_label = st.selectbox(
        "Période de capitalisation",
        ["Trimestrielle (tous les 3 mois)", "Semestrielle (tous les 6 mois)"],
    )
    frequency_months = 3 if frequency_label.startswith("Trimestrielle") else 6
    projection_end = add_months(opening_date, 12)
    st.caption(
        f"Projection du {opening_date.strftime('%d/%m/%Y')} au {projection_end.strftime('%d/%m/%Y')}. "
        f"Les intérêts sont ajoutés au solde {frequency_label.lower()} après une opération postérieure à l’échéance."
    )

    if "savings_operations" not in st.session_state:
        st.session_state.savings_operations = []

    st.markdown("### Ajouter une opération")
    with st.form("savings_operation_form", clear_on_submit=True):
        operation_cols = st.columns([1.2, 1, 1])
        operation_date = operation_cols[0].date_input(
            "Date de l’opération",
            value=opening_date,
            min_value=opening_date,
            max_value=projection_end,
        )
        operation_type = operation_cols[1].selectbox("Type d’opération", ["Versement", "Retrait"])
        amount = operation_cols[2].number_input(
            "Montant (TND)", min_value=0.001, value=100.0, step=50.0
        )
        submitted = st.form_submit_button("＋ Ajouter au tableau", type="primary")

    if submitted:
        st.session_state.savings_operations.append((operation_date, operation_type, amount))
        st.success("Opération ajoutée au tableau du compte.")

    operations = st.session_state.savings_operations
    if not operations:
        st.markdown(
            "<div class='section-card'><b>Aucune opération pour le moment</b><br>"
            "<span class='small-note'>Renseignez une date, un type et un montant, puis ajoutez l’opération au tableau.</span></div>",
            unsafe_allow_html=True,
        )

    try:
        result = calculate_savings(initial, rate, operations, opening_date, frequency_months)
        st.markdown("### Synthèse après un an")
        m1, m2, m3 = st.columns(3)
        m1.metric("Capital initial", format_tnd(initial))
        m2.metric("Intérêts capitalisés", format_tnd(result["interest"]))
        m3.metric("Capital acquis", format_tnd(result["capital"]))

        st.markdown("### Tableau du compte d’épargne")
        st.dataframe(result["statement"], use_container_width=True, hide_index=True)

        with st.expander("Voir le détail du calcul des intérêts"):
            rows = [{
                "Du": start.strftime('%d/%m/%Y'),
                "Au": end.strftime('%d/%m/%Y'),
                "Solde (TND)": float(balance),
                "Jours (30/360)": days,
                "Nombres": float(number),
            } for start, end, balance, days, number in result["segments"]]
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.caption("Aucun intérêt n’a encore été capitalisé. Il apparaîtra après une opération dont la date de valeur est postérieure à une échéance.")

        with st.expander("Comprendre la méthode"):
            st.write(
                "Le tableau présente le capital à l’ouverture, chaque versement ou retrait avec sa date d’opération "
                "et sa date de valeur, ainsi que les intérêts capitalisés lorsqu’une opération survient après une échéance. "
                "Les versements prennent effet le 1er ou le 16 du mois selon leur date d’opération ; les retraits prennent "
                "effet au début de la quinzaine correspondante. Les intérêts sont calculés selon une année commerciale "
                f"de 360 jours, puis ajoutés au solde à chaque échéance {frequency_label.lower()} après cette opération."
            )

    except ValueError as error:
        st.error(str(error))
