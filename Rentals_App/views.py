from django.shortcuts import render
from django.db import connection
from datetime import datetime


def home(request):
    return render(request, 'home.html')


def dictfetchall(cursor):
    """Return all rows from a cursor as a dict."""
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _year_expr(column_name: str) -> str:

    if connection.vendor == 'mssql':
        return f"CAST(strftime('%Y', {column_name}) AS INTEGER)"
    return f"YEAR({column_name})"


def query_page(request):
    # Query 1 : For each apartment of a legal owner, not rented > 3 years,
    # find the renter with the highest cost contract.
    SQL1 = f"""
    SELECT DISTINCT
        r.aID AS [Apartment ID],
        r.renterID AS [Highest Cost Renter]
    FROM Rentals r
    JOIN (
        SELECT qa.aID, MAX(r2.cost) AS max_cost
        FROM (
            SELECT r1.aID
            FROM Rentals r1
            JOIN Apartments a1 ON r1.aID = a1.aID
            WHERE a1.ownerID IN (
                SELECT o.ownerID
                FROM Owners o
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM Rentals r0
                    JOIN Apartments a0 ON r0.aID = a0.aID
                    WHERE a0.ownerID = o.ownerID
                      AND r0.rYear < ({_year_expr('o.bDate')} + 18)
                )
            )
            GROUP BY r1.aID
            HAVING COUNT(DISTINCT r1.rYear) <= 3
        ) AS qa
        JOIN Rentals r2 ON qa.aID = r2.aID
        GROUP BY qa.aID
    ) AS m
      ON r.aID = m.aID AND r.cost = m.max_cost
    ORDER BY r.aID ASC, r.renterID ASC;
    """

    # Query 2: Cities where minimalist renters lived with minimalist owners.
    SQL2 = """
    SELECT DISTINCT a.city AS [City]
    FROM Rentals r
    JOIN Apartments a ON r.aID = a.aID
    JOIN (
        -- Minimalist owners: never >3 renters in any apartment in any year
        SELECT o.ownerID
        FROM Owners o
        WHERE NOT EXISTS (
            SELECT 1
            FROM Apartments a1
            JOIN Rentals r1 ON a1.aID = r1.aID
            WHERE a1.ownerID = o.ownerID
            GROUP BY a1.aID, r1.rYear
            HAVING COUNT(r1.renterID) > 3
        )
    ) AS mo ON a.ownerID = mo.ownerID
    JOIN (
        -- Minimalist renters: never paid >2000 and never lived alone
        SELECT r1.renterID
        FROM Rentals r1
        GROUP BY r1.renterID
        HAVING MAX(r1.cost) <= 2000
           AND NOT EXISTS (
                SELECT 1
                FROM Rentals r2
                WHERE r2.renterID = r1.renterID
                  AND (
                        SELECT COUNT(*)
                        FROM Rentals r3
                        WHERE r3.aID = r2.aID AND r3.rYear = r2.rYear
                      ) = 1
           )
    ) AS mr ON r.renterID = mr.renterID
    ORDER BY a.city ASC;
    """

    # Query 3 : Diverse owners (born >= 2000) who rented to problematic renters.
    SQL3 = f"""
    SELECT
        do.oName AS [Name],
        do.bDate AS [Birth Date],
        COUNT(DISTINCT r.aID) AS [Problematic Apartments]
    FROM (
        -- Diverse owners: >=1 apt; all apts in different cities; none in residenceCity
        SELECT o.ownerID, o.oName, o.bDate
        FROM Owners o
        WHERE {_year_expr('o.bDate')} >= 2000
          AND (SELECT COUNT(*) FROM Apartments WHERE ownerID = o.ownerID) > 0
          AND (
                SELECT COUNT(DISTINCT a.city)
                FROM Apartments a WHERE a.ownerID = o.ownerID
              ) = (
                SELECT COUNT(a2.aID)
                FROM Apartments a2 WHERE a2.ownerID = o.ownerID
              )
          AND NOT EXISTS (
                SELECT 1 FROM Apartments a3
                WHERE a3.ownerID = o.ownerID AND a3.city = o.residenceCity
          )
    ) AS do
    JOIN Apartments a ON do.ownerID = a.ownerID
    JOIN Rentals r ON a.aID = r.aID
    JOIN (
        -- Problematic renters: never lived with the same partner twice (across years)
        SELECT r4.renterID
        FROM Rentals r4
        GROUP BY r4.renterID
        HAVING NOT EXISTS (
            SELECT 1
            FROM (
                SELECT r1.renterID AS renter, r2.renterID AS partner
                FROM Rentals r1
                JOIN Rentals r2
                  ON r1.aID = r2.aID
                 AND r1.rYear = r2.rYear
                 AND r1.renterID <> r2.renterID
            ) AS pairs
            WHERE pairs.renter = r4.renterID
            GROUP BY pairs.renter, pairs.partner
            HAVING COUNT(*) > 1
        )
    ) AS pr ON r.renterID = pr.renterID
    GROUP BY do.ownerID, do.oName, do.bDate
    ORDER BY do.bDate DESC, do.ownerID ASC;
    """

    with connection.cursor() as cursor:
        cursor.execute(SQL1)
        result1 = dictfetchall(cursor)

        cursor.execute(SQL2)
        result2 = dictfetchall(cursor)

        cursor.execute(SQL3)
        result3 = dictfetchall(cursor)

    return render(request, 'queries.html', {
        'result1': result1,
        'result2': result2,
        'result3': result3,
    })


def add_rental(request):
    message, error, warning = "", "", ""

    with connection.cursor() as cursor:
        cursor.execute("SELECT aID, city FROM Apartments ORDER BY aID")
        apartments = [{'aid': row[0], 'city': row[1]} for row in cursor.fetchall()]

    if request.method == "POST":
        try:
            renterid = int(request.POST.get("renterid"))
            aid = int(request.POST.get("aid"))
            cost = int(request.POST.get("cost"))
            ryear = datetime.now().year


            if renterid <= 0:
                error = "Renter ID must be a positive integer."
            elif cost <= 500:
                error = "Monthly cost must be an integer greater than 500."
            else:
                with connection.cursor() as cursor:

                    cursor.execute(
                        "SELECT 1 FROM Rentals WHERE renterID = %s AND rYear = %s",
                        [renterid, ryear]
                    )
                    if cursor.fetchone():
                        error = "A rental agreement for this renter and year already exists."
                    else:

                        cursor.execute(
                            "SELECT TOP 1 1 FROM Rentals WHERE renterID = %s",
                            [renterid]
                        )
                        if not cursor.fetchone():
                            error = "Renter ID does not exist in the system."
                        else:

                            cursor.execute(
                                "INSERT INTO Rentals (aID, renterID, rYear, cost) VALUES (%s, %s, %s, %s)",
                                [aid, renterid, ryear, cost]
                            )
                            message = "Rental agreement added successfully."


                            cursor.execute(
                                "SELECT COUNT(*) FROM Rentals WHERE aID = %s AND rYear = %s",
                                [aid, ryear]
                            )
                            if cursor.fetchone()[0] > 5:
                                warning = "Warning: More than 5 renters are now in this apartment for this year."
        except (ValueError, TypeError):
            error = "Invalid input. Please ensure all fields are correctly filled."

    return render(request, 'add_rental.html', {
        'apartments': apartments, 'message': message, 'error': error, 'warning': warning
    })


def owner_search(request):
    owners = None
    if request.method == 'POST' and 'prefix' in request.POST:
        prefix = request.POST.get('prefix', '').strip()
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT ownerID, oName FROM Owners WHERE LOWER(oName) LIKE LOWER(%s)",
                [prefix + '%']
            )
            owners = cursor.fetchall()
    return render(request, 'owner_search.html', {'owners': owners})


def owner_analysis(request):
    analysis, analysis_error = None, None
    if request.method == 'POST' and 'owner_id' in request.POST:
        try:
            owner_id = int(request.POST.get('owner_id'))
            with connection.cursor() as cursor:
                cursor.execute("SELECT residenceCity FROM Owners WHERE ownerID = %s", [owner_id])
                owner_data = cursor.fetchone()

                if owner_data:
                    residence_city = owner_data[0]
                    # Num apartments
                    cursor.execute("SELECT COUNT(*) FROM Apartments WHERE ownerID = %s", [owner_id])
                    num_apartments = cursor.fetchone()[0]
                    # Avg roommates
                    avg_roommates = "NA"
                    if num_apartments > 0:
                        cursor.execute("""
                            SELECT AVG(CAST(rental_counts.c AS FLOAT)) FROM (
                                SELECT COUNT(r.renterID) AS c
                                FROM Rentals r
                                JOIN Apartments a ON r.aID = a.aID
                                WHERE a.ownerID = %s
                                GROUP BY r.aID, r.rYear
                            ) AS rental_counts
                        """, [owner_id])
                        result = cursor.fetchone()[0]
                        if result is not None:
                            avg_roommates = f"{result:.2f}"
                    # Other owners in city
                    cursor.execute(
                        "SELECT COUNT(*) FROM Owners WHERE residenceCity = %s AND ownerID != %s",
                        [residence_city, owner_id]
                    )
                    other_owners = cursor.fetchone()[0]

                    analysis = {
                        'apartments': num_apartments,
                        'avg_roommates': avg_roommates,
                        'other_owners': other_owners,
                    }
                else:
                    analysis_error = "Owner not found in the system."
        except (ValueError, TypeError):
            analysis_error = "Invalid Owner ID. Please enter a number."

    return render(request, 'owner_search.html', {'analysis': analysis, 'analysis_error': analysis_error})
