-- Ejecutar manualmente contra la DB existente (vía psql o Adminer) en cada entorno
-- ya desplegado. En instalaciones nuevas no es necesario: create_all() crea la
-- columna directamente al crear la tabla "persons" por primera vez.
ALTER TABLE persons ADD COLUMN IF NOT EXISTS keycloak_id UUID UNIQUE;
