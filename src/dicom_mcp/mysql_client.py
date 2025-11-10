"""Utility client for interacting with the mini-RIS MySQL database."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import mysql.connector
from mysql.connector import pooling


logger = logging.getLogger("dicom_mcp.mysql")


@dataclass
class MiniRisConnectionSettings:
    host: str
    port: int
    user: str
    password: str
    database: str
    pool_name: str = "mini_ris_pool"
    pool_size: int = 5


class MiniRisClient:
    """Thin wrapper around the MySQL connector for the mini-RIS schema."""

    def __init__(self, config: MiniRisConnectionSettings) -> None:
        self.config = config
        logger.info(
            "Initializing Mini-RIS MySQL pool at %s:%s/%s",
            config.host,
            config.port,
            config.database,
        )
        self._pool = pooling.MySQLConnectionPool(
            pool_name=config.pool_name,
            pool_size=config.pool_size,
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            autocommit=True,
            charset="utf8mb4",
            use_pure=True,
        )

    @contextmanager
    def _get_connection(self):
        conn = self._pool.get_connection()
        try:
            yield conn
        finally:
            conn.close()

    def ping(self) -> Dict[str, Any]:
        """Verify connectivity to the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT 1 AS alive")
            result = cursor.fetchone()
            cursor.close()
            return {
                "success": True,
                "message": "Mini-RIS database connection successful",
                "result": result,
            }

    def list_patients(
        self,
        *,
        mrn: Optional[str] = None,
        name_query: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Return a filtered list of patients from the mini-RIS schema."""

        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        filters: List[str] = []
        params: List[Any] = []

        if mrn:
            filters.append("mrn = %s")
            params.append(mrn)

        if name_query:
            filters.append("(given_name LIKE %s OR family_name LIKE %s)")
            like_term = f"%{name_query}%"
            params.extend([like_term, like_term])

        where_clause = " WHERE " + " AND ".join(filters) if filters else ""

        sql = f"""
            SELECT
                patient_id,
                mrn,
                given_name,
                family_name,
                date_of_birth,
                sex,
                country_code,
                preferred_language,
                phone,
                email,
                city,
                state,
                postal_code,
                created_at,
                updated_at
            FROM patients
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
        """

        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()

        return {
            "success": True,
            "count": len(rows),
            "patients": rows,
            "limit": limit,
            "offset": offset,
            "filters": {
                "mrn": mrn,
                "name_query": name_query,
            },
        }

    def get_order_for_mwl(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Fetch order data with all related information needed for MWL creation.
        
        Args:
            order_id: The order ID to fetch
            
        Returns:
            Dictionary with order, patient, procedure, and provider data, or None if not found
        """
        sql = """
            SELECT 
                o.order_id,
                o.order_number,
                o.accession_number,
                o.modality_code,
                o.scheduled_start,
                o.status AS order_status,
                o.priority,
                o.reason_description,
                p.patient_id,
                p.mrn,
                p.given_name,
                p.family_name,
                p.date_of_birth,
                p.sex,
                op.procedure_code,
                op.procedure_description,
                op.laterality,
                proc.typical_views,
                proc.typical_image_count,
                prov.given_name AS performing_physician_given,
                prov.family_name AS performing_physician_family,
                ordering_prov.given_name AS ordering_physician_given,
                ordering_prov.family_name AS ordering_physician_family
            FROM orders o
            INNER JOIN patients p ON o.patient_id = p.patient_id
            INNER JOIN order_procedures op ON o.order_id = op.order_id
            INNER JOIN procedures proc ON op.procedure_code = proc.procedure_code
            LEFT JOIN providers prov ON o.performing_provider_id = prov.provider_id
            LEFT JOIN providers ordering_prov ON o.ordering_provider_id = ordering_prov.provider_id
            WHERE o.order_id = %s
            LIMIT 1
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (order_id,))
            result = cursor.fetchone()
            cursor.close()
            
        return result

