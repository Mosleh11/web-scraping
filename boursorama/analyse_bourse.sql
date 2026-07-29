-- Defi 3 : lecture analytique du palmares Boursorama.

-- 1) Top 5 hausses du jour
SELECT libelle, variation, cours FROM actions ORDER BY variation DESC LIMIT 5;

-- 2) Top 5 baisses du jour
SELECT libelle, variation, cours FROM actions ORDER BY variation ASC LIMIT 5;

-- 3) Volumes anormalement eleves : plus de 2x la MEDIANE
--    (l'enonce ecrit AVG dans une requete commentee "mediane" : sur des volumes
--     boursiers la moyenne est tiree par quelques geants, voir README)
SELECT libelle, volume, cours, variation
FROM actions
WHERE volume > 2 * (
    SELECT volume FROM actions ORDER BY volume LIMIT 1
    OFFSET (SELECT COUNT(*) FROM actions) / 2
)
ORDER BY volume DESC;

-- 4) Comparaison des deux seuils
SELECT
    (SELECT AVG(volume) FROM actions)                                    AS moyenne,
    (SELECT volume FROM actions ORDER BY volume
     LIMIT 1 OFFSET (SELECT COUNT(*) FROM actions) / 2)                  AS mediane,
    (SELECT COUNT(*) FROM actions WHERE volume > 2*(SELECT AVG(volume) FROM actions))   AS nb_sur_moyenne,
    (SELECT COUNT(*) FROM actions WHERE volume > 2*(SELECT volume FROM actions ORDER BY volume
     LIMIT 1 OFFSET (SELECT COUNT(*) FROM actions) / 2))                 AS nb_sur_mediane;
