-- Query 1: Highest Cost Renter
DROP VIEW IF EXISTS Query1_HighestCostRenter;
GO
CREATE VIEW Query1_HighestCostRenter AS
SELECT DISTINCT r.aID AS ApartmentID, r.renterID AS HighestCostRenter
FROM Rentals r
JOIN (
    SELECT qa.aID, MAX(r_inner.cost) AS max_cost
    FROM (
        SELECT r2.aID
        FROM Rentals r2
        JOIN Apartments a2 ON r2.aID = a2.aID
        WHERE a2.ownerID IN (
            SELECT o.ownerID
            FROM Owners o
            WHERE NOT EXISTS (
                SELECT 1
                FROM Rentals r3
                JOIN Apartments a3 ON r3.aID = a3.aID
                WHERE a3.ownerID = o.ownerID
                  AND r3.rYear < (YEAR(o.bDate) + 18)
            )
        )
        GROUP BY r2.aID
        HAVING COUNT(DISTINCT r2.rYear) <= 3
    ) qa
    JOIN Rentals r_inner ON qa.aID = r_inner.aID
    GROUP BY qa.aID
) m ON r.aID = m.aID AND r.cost = m.max_cost;
GO

-- Query 2: Minimalist Cities
DROP VIEW IF EXISTS Query2_MinimalistCities;
GO
CREATE VIEW Query2_MinimalistCities AS
SELECT DISTINCT a.city AS City
FROM Rentals r
JOIN Apartments a ON r.aID = a.aID
JOIN (
    SELECT o.ownerID
    FROM Owners o
    WHERE NOT EXISTS (
        SELECT 1
        FROM Apartments a_inner
        JOIN Rentals r_inner ON a_inner.aID = r_inner.aID
        WHERE a_inner.ownerID = o.ownerID
        GROUP BY a_inner.aID, r_inner.rYear
        HAVING COUNT(r_inner.renterID) > 3
    )
) mo ON a.ownerID = mo.ownerID
JOIN (
    SELECT r1.renterID
    FROM Rentals r1
    WHERE NOT EXISTS (
        SELECT 1
        FROM Rentals r2
        WHERE r2.renterID = r1.renterID
          AND (
            SELECT COUNT(*)
            FROM Rentals r3
            WHERE r3.aID = r2.aID AND r3.rYear = r2.rYear
          ) = 1
    )
    GROUP BY r1.renterID
    HAVING MAX(r1.cost) <= 2000
) mr ON r.renterID = mr.renterID;
GO

-- Query 3: Diverse Owners Problematic
DROP VIEW IF EXISTS Query3_DiverseOwnersProblematic;
GO
CREATE VIEW Query3_DiverseOwnersProblematic AS
SELECT do.oName AS Name, do.bDate AS BirthDate, COUNT(DISTINCT r.aID) AS ProblematicApartments
FROM (
    SELECT o.ownerID, o.oName, o.bDate
    FROM Owners o
    WHERE YEAR(o.bDate) >= 2000
      AND EXISTS (SELECT 1 FROM Apartments a0 WHERE a0.ownerID = o.ownerID)
      AND (
        SELECT COUNT(DISTINCT a1.city)
        FROM Apartments a1
        WHERE a1.ownerID = o.ownerID
      ) = (
        SELECT COUNT(a2.aID)
        FROM Apartments a2
        WHERE a2.ownerID = o.ownerID
      )
      AND NOT EXISTS (
        SELECT 1
        FROM Apartments a3
        WHERE a3.ownerID = o.ownerID AND a3.city = o.residenceCity
      )
) do
JOIN Apartments a ON do.ownerID = a.ownerID
JOIN Rentals r ON a.aID = r.aID
JOIN (
    SELECT r_outer.renterID
    FROM Rentals r_outer
    WHERE NOT EXISTS (
        SELECT 1
        FROM (
            SELECT
                r1.renterID AS renter,
                r2.renterID AS partner
            FROM Rentals r1
            JOIN Rentals r2
                ON r1.aID = r2.aID
                AND r1.rYear = r2.rYear
                AND r1.renterID <> r2.renterID
            WHERE r1.renterID = r_outer.renterID
        ) pairs
        GROUP BY renter, partner
        HAVING COUNT(*) > 1
    )
    GROUP BY r_outer.renterID
) pr ON r.renterID = pr.renterID
GROUP BY do.oName, do.bDate, do.ownerID;
GO