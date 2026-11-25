from datetime import date
from decimal import Decimal, ROUND_HALF_UP


EURO = Decimal("0.01")


def money(value):
    return value.quantize(EURO, rounding=ROUND_HALF_UP)


def simple_interest(capital, annual_rate_percent, years):
    """Calcule les intérêts simples: I = C * t * n."""
    c = Decimal(str(capital))
    t = Decimal(str(annual_rate_percent)) / Decimal("100")
    n = Decimal(str(years))
    return money(c * t * n)


def next_month(value):
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def value_date(operation_date, operation_type):
    """Applique la règle des quinzaines pour une année commerciale de 360 jours."""
    if operation_type not in ("versement", "retrait"):
        raise ValueError("Type d'opération invalide.")

    if operation_type == "versement":
        if operation_date.day == 1 or operation_date.day == 16:
            return operation_date
        if operation_date.day < 16:
            return date(operation_date.year, operation_date.month, 16)
        return next_month(operation_date)

    if operation_date.day <= 15:
        return date(operation_date.year, operation_date.month, 1)
    return date(operation_date.year, operation_date.month, 16)


def days_360(start, end):
    """Nombre de jours selon l'année commerciale de 360 jours."""
    return (
        (end.year - start.year) * 360
        + (end.month - start.month) * 30
        + (min(end.day, 30) - min(start.day, 30))
    )


def calculate_savings(initial_balance, annual_rate_percent, operations, year):
    """Calcule les intérêts simples annuels d'un compte d'épargne."""
    balance = Decimal(str(initial_balance))
    rate = Decimal(str(annual_rate_percent))
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    segments = []
    ignored = []

    valued_operations = []
    for operation_date, operation_type, amount in operations:
        if operation_date < start or operation_date >= end:
            ignored.append((operation_date, operation_type, amount))
            continue
        if operation_type not in ("versement", "retrait"):
            raise ValueError("Type d'opération invalide.")

        amount = Decimal(str(amount))
        if amount < 0:
            raise ValueError("Les montants doivent être positifs.")
        signed_amount = amount if operation_type == "versement" else -amount
        valued_operations.append(
            (value_date(operation_date, operation_type), operation_date, operation_type,
             signed_amount)
        )

    valued_operations.sort(key=lambda item: (item[0], item[1], item[2]))
    segment_start = start

    for value, operation_date, operation_type, signed_amount in valued_operations:
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

    total_numbers = sum((segment[4] for segment in segments), Decimal("0"))
    divisor = Decimal("360") / rate
    interest = money(total_numbers / divisor)

    return {
        "initial_balance": Decimal(str(initial_balance)),
        "balance_without_interest": balance,
        "capital_acquired": money(balance + interest),
        "interest": interest,
        "total_numbers": money(total_numbers),
        "divisor": divisor,
        "segments": segments,
        "ignored": ignored,
    }


def read_decimal(prompt):
    while True:
        try:
            value = Decimal(input(prompt).strip().replace(",", "."))
            if value < 0:
                raise ValueError
            return value
        except (ArithmeticError, ValueError):
            print("Veuillez saisir un nombre positif valide.")


def read_positive_decimal(prompt):
    while True:
        value = read_decimal(prompt)
        if value > 0:
            return value
        print("La valeur doit être strictement supérieure à zéro.")


def read_year():
    while True:
        try:
            year = int(input("Année civile (ex. 2025): ").strip())
            if 1900 <= year <= 2100:
                return year
            raise ValueError
        except ValueError:
            print("Veuillez saisir une année entre 1900 et 2100.")


def read_date(prompt, year):
    while True:
        try:
            text = input(prompt).strip()
            day, month, entered_year = (int(part) for part in text.split("/"))
            if entered_year != year:
                raise ValueError
            return date(year, month, day)
        except ValueError:
            print(f"Veuillez saisir une date valide au format jj/mm/{year}.")


def interactive():
    print("\nCompte d'épargne - intérêts simples")
    print("Méthode des quinzaines - année commerciale de 360 jours\n")

    year = read_year()
    initial = read_decimal("Solde au 01/01: ")
    rate = read_positive_decimal("Taux annuel en %: ")
    operations = []

    while True:
        answer = input("Ajouter une opération? (o/n): ").strip().lower()
        if answer not in ("o", "n"):
            print("Répondez par 'o' ou 'n'.")
            continue
        if answer == "n":
            break

        operation_date = read_date("Date (jj/mm/aaaa): ", year)
        operation_type = input("Type (v = versement, r = retrait): ").strip().lower()
        if operation_type not in ("v", "r"):
            print("Veuillez saisir v ou r.")
            continue
        operation_type = "versement" if operation_type == "v" else "retrait"
        amount = read_positive_decimal("Montant positif: ")
        operations.append((operation_date, operation_type, amount))

    result = calculate_savings(initial, rate, operations, year)

    print("\nRelevé des opérations")
    print(f"01/01/{year}  Solde initial                 {money(initial):>10.2f}")
    for operation_date, operation_type, amount in operations:
        if operation_date >= date(year, 1, 1) and operation_date < date(year + 1, 1, 1):
            value = value_date(operation_date, operation_type)
            print(
                f"{operation_date.strftime('%d/%m/%Y')} "
                f"{operation_type.capitalize():<10} {money(amount):>10.2f} "
                f"valeur {value.strftime('%d/%m/%Y')}"
            )

    print("\nCalcul des nombres")
    print(f"{'Du':<12}{'Au':<12}{'Solde':>12}{'Jours':>8}{'Nombres':>14}")
    for start, end, balance, days, number in result["segments"]:
        print(
            f"{start.strftime('%d/%m/%Y'):<12}"
            f"{end.strftime('%d/%m/%Y'):<12}"
            f"{balance:>12.2f}{days:>8}{number:>14.2f}"
        )

    print(f"\nTotal des nombres: {result['total_numbers']:.2f}")
    print(f"Diviseur: {result['divisor']:.4f}")
    print(f"Intérêts de l'année: {result['interest']:.2f}")
    print(f"Capital acquis au 31/12/{year}: {result['capital_acquired']:.2f}")

    if result["ignored"]:
        print(f"\n{len(result['ignored'])} opération(s) hors de l'année ont été ignorée(s).")


if __name__ == "__main__":
    interactive()