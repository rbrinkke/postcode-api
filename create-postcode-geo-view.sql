-- Permanente view voor postcode geolocatie
-- Doel: Geef 1 lat/lon punt per postcode voor activiteiten app
-- Gebruikt index: adridx on nums(postcode,huisnummer,huisletter,huistoevoeging)

DROP VIEW IF EXISTS postcode_geo;

CREATE VIEW postcode_geo AS 
SELECT 
    postcode,
    lat,
    lon,
    woonplaats
FROM unilabel
WHERE postcode IN (
    SELECT postcode 
    FROM nums 
    WHERE status != 'Naamgeving ingetrokken'
    GROUP BY postcode
)
GROUP BY postcode;

-- Test query:
-- SELECT * FROM postcode_geo WHERE postcode = '7557NX';

-- Performance check:
-- EXPLAIN QUERY PLAN SELECT * FROM postcode_geo WHERE postcode = '7557NX';