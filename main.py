import streamlit as st
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

EURO = Decimal("0.01")


def money(value):
    return value.quantize(EURO, rounding=ROUND_HALF_UP)


def next_month(value):
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def value_date(operation_date, operation_type):
    """Applique la règle des quinzaines sur une année commerciale de 360 jours."""
    if operation_type not in ("Versement", "Retrait"):
        raise ValueError("Type d'opération invalide.")

    if operation_type == "Versement":
        if operation_date.day in (1, 16):
            return operation_date
        if operation_date.day < 16:
            return date(operation_date.year, operation_date.month, 16)
        return next_month(operation_date)

    if operation_date.day <= 15:
        return date(operation_date.year, operation_date.month, 1)
    return date(operation_date.year, operation_date.month, 16)


def days_360(start, end):
    """Nombre de jours selon une année commerciale de 360 jours."""
    return (
        (end.year - start.year) * 360
        + (end.month - start.month) * 30
        + min(end.day, 30)
        - min(start.day, 30)
    )


def calculate_savings(initial_balance, annual_rate, operations, year):
    balance = Decimal(str(initial_balance))
    rate = Decimal(str(annual_rate))
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    valued_operations = []
    segments = []

    for operation_date, operation_type, amount in operations:
        if operation_date < start or operation_date >= end:
            continue

        amount = Decimal(str(amount))
        signed_amount = amount if operation_type == "Versement" else -amount
        valued_operations.append(
            (value_date(operation_date, operation_type), operation_date, signed_amount)
        )

    valued_operations.sort(key=lambda item: (item[0], item[1]))
    segment_start = start

    for value, operation_date, signed_amount in valued_operations:
        if value < start:
            value = start
        if value >= end:
            continue

        days = days_360(segment_start, value)
        if days > 0:
            number = balance * Decimal(days) / Decimal("100")
            segments.append((segment_start, value, balance, days, number))

        balance += signed_amount
        segment_start = value

    days = days_360(segment_start, end)
    if days > 0:
        number = balance * Decimal(days) / Decimal("100")
        segments.append((segment_start, end, balance, days, number))

    total_numbers = sum(
        (segment[4] for segment in segments),
        Decimal("0"),
    )

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


st.set_page_config(page_title="Compte d'épargne", page_icon="💰")
st.title("Compte d'épargne")
st.caption("Intérêts simples — méthode des quinzaines — année commerciale de 360 jours")

year = st.number_input("Année", min_value=1900, max_value=2100, value=2025)
initial = st.number_input("Solde initial au 1er janvier (€)", min_value=0.0, value=1000.0)
rate = st.number_input("Taux annuel (%)", min_value=0.01, value=5.0)

st.subheader("Opérations")
count = st.number_input("Nombre d'opérations", min_value=0, max_value=100, value=0)
operations = []

for index in range(int(count)):
    cols = st.columns(4)
    operation_date = cols[0].date_input(
        f"Date {index + 1}",
        value=date(int(year), 1, 1),
        key=f"date_{index}",
    )
    operation_type = cols[1].selectbox(
        f"Type {index + 1}",
        ["Versement", "Retrait"],
        key=f"type_{index}",
    )
    amount = cols[2].number_input(
        f"Montant {index + 1}",
        min_value=0.0,
        value=100.0,
        key=f"amount_{index}",
    )
    operations.append((operation_date, operation_type, amount))

if st.button("Calculer", type="primary"):
    try:
        result = calculate_savings(initial, rate, operations, int(year))

        col1, col2, col3 = st.columns(3)
        col1.metric("Solde sans intérêts", f"{result['balance']:,.2f} €")
        col2.metric("Intérêts", f"{result['interest']:,.2f} €")
        col3.metric("Capital acquis", f"{result['capital']:,.2f} €")

        st.subheader("Calcul des nombres")
        rows = [
            {
                "Du": start.strftime("%d/%m/%Y"),
                "Au": end.strftime("%d/%m/%Y"),
                "Solde": float(money(balance)),
                "Jours": days,
                "Nombres": float(money(number)),
            }
            for start, end, balance, days, number in result["segments"]
        ]

        st.dataframe(rows, use_container_width=True)
        st.write(f"**Total des nombres :** {money(result['total_numbers']):,.2f}")
        st.write(f"**Diviseur :** {result['divisor']:,.4f}")
    except ValueError as error:
        st.error(str(error))
