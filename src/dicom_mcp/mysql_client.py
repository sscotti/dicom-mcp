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

    def list_orders(
        self,
        *,
        mrn: Optional[str] = None,
        status: Optional[str] = None,
        accession_number: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Return a filtered list of orders from the mini-RIS schema.
        
        Args:
            mrn: Filter by patient MRN
            status: Filter by order status (Requested, Scheduled, InProgress, Completed, Cancelled)
            accession_number: Filter by accession number
            limit: Maximum number of rows to return (1-100)
            offset: Pagination offset
            
        Returns:
            Dictionary with orders list and metadata
        """
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        
        filters: List[str] = []
        params: List[Any] = []
        
        if mrn:
            filters.append("p.mrn = %s")
            params.append(mrn)
        
        if status:
            filters.append("o.status = %s")
            params.append(status)
        
        if accession_number:
            filters.append("o.accession_number = %s")
            params.append(accession_number)
        
        where_clause = " WHERE " + " AND ".join(filters) if filters else ""
        
        sql = f"""
            SELECT
                o.order_id,
                o.order_number,
                o.accession_number,
                o.patient_id,
                p.mrn,
                p.given_name,
                p.family_name,
                o.modality_code,
                o.status,
                o.priority,
                o.order_datetime,
                o.scheduled_start,
                o.reason_description,
                o.created_at,
                o.updated_at
            FROM orders o
            INNER JOIN patients p ON o.patient_id = p.patient_id
            {where_clause}
            ORDER BY o.order_datetime DESC
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
            "orders": rows,
            "limit": limit,
            "offset": offset,
            "filters": {
                "mrn": mrn,
                "status": status,
                "accession_number": accession_number,
            },
        }

    def create_mwl_task(
        self,
        order_id: int,
        scheduled_station_aet: str,
        scheduled_start: datetime,
        mwl_payload: Dict[str, Any],
        scheduled_station_name: Optional[str] = None,
        scheduled_end: Optional[datetime] = None,
        scheduled_performing_provider_id: Optional[int] = None,
    ) -> int:
        """Create an MWL task record when MWL is created from an order.
        
        Args:
            order_id: The order ID
            scheduled_station_aet: AE Title of the scheduled station
            scheduled_station_name: Optional name of the scheduled station
            scheduled_start: Scheduled start datetime
            scheduled_end: Optional scheduled end datetime
            scheduled_performing_provider_id: Optional performing provider ID
            mwl_payload: The MWL payload JSON
            
        Returns:
            The created mwl_task_id
        """
        import json
        
        sql = """
            INSERT INTO mwl_tasks (
                order_id, scheduled_station_aet, scheduled_station_name,
                scheduled_start, scheduled_end, scheduled_performing_provider_id,
                status, mwl_payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    order_id,
                    scheduled_station_aet,
                    scheduled_station_name,
                    scheduled_start,
                    scheduled_end,
                    scheduled_performing_provider_id,
                    'Scheduled',  # Initial status
                    json.dumps(mwl_payload),
                ),
            )
            mwl_task_id = cursor.lastrowid
            conn.commit()
            cursor.close()
        
        return mwl_task_id

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
                o.scheduled_end,
                o.status AS order_status,
                o.priority,
                o.reason_description,
                o.performing_provider_id,
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

    def get_study_by_accession(self, accession_number: str) -> Optional[Dict[str, Any]]:
        """Fetch complete study information by accession number for reporting.
        
        Args:
            accession_number: The accession number to search for
            
        Returns:
            Dictionary with study, patient, order, and procedure data, or None if not found
        """
        sql = """
            SELECT 
                s.imaging_study_id,
                s.study_instance_uid,
                s.study_started,
                s.study_completed,
                s.status AS study_status,
                s.number_of_series,
                s.number_of_instances,
                o.order_id,
                o.order_number,
                o.accession_number,
                o.modality_code,
                o.reason_description,
                o.image_generation_prompt,
                o.report_findings_description,
                DATE(COALESCE(s.study_started, o.scheduled_start)) AS study_date,
                TIME(COALESCE(s.study_started, o.scheduled_start)) AS study_time,
                COALESCE(op.procedure_description, o.reason_description, 'Imaging Study') AS study_description,
                p.patient_id,
                p.mrn,
                p.given_name,
                p.family_name,
                p.date_of_birth,
                p.sex,
                op.procedure_code,
                op.procedure_description,
                prov.provider_id AS performing_provider_id,
                prov.given_name AS performing_physician_given,
                prov.family_name AS performing_physician_family,
                ordering_prov.provider_id AS ordering_provider_id,
                ordering_prov.given_name AS ordering_physician_given,
                ordering_prov.family_name AS ordering_physician_family
            FROM imaging_studies s
            INNER JOIN orders o ON s.order_id = o.order_id
            INNER JOIN patients p ON o.patient_id = p.patient_id
            LEFT JOIN order_procedures op ON o.order_id = op.order_id
            LEFT JOIN providers prov ON o.performing_provider_id = prov.provider_id
            LEFT JOIN providers ordering_prov ON o.ordering_provider_id = ordering_prov.provider_id
            WHERE o.accession_number = %s
            LIMIT 1
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (accession_number,))
            result = cursor.fetchone()
            cursor.close()
            
        return result

    def get_report_by_id(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a report by its report_id with all related study/patient data.
        
        Args:
            report_id: The report ID to fetch
            
        Returns:
            Dictionary with report, study, patient, and provider data, or None if not found
        """
        sql = """
            SELECT 
                r.report_id,
                r.report_number,
                r.report_status,
                r.report_datetime,
                r.report_text,
                r.impression,
                r.dicom_sop_instance_uid,
                r.dicom_series_instance_uid,
                r.created_at,
                r.updated_at,
                s.imaging_study_id,
                s.study_instance_uid,
                s.study_started,
                s.study_completed,
                DATE(COALESCE(s.study_started, o.scheduled_start)) AS study_date,
                TIME(COALESCE(s.study_started, o.scheduled_start)) AS study_time,
                COALESCE(op.procedure_description, o.reason_description, 'Imaging Study') AS study_description,
                o.modality_code,
                o.accession_number,
                o.order_number,
                o.reason_description,
                p.patient_id,
                p.mrn,
                p.given_name,
                p.family_name,
                p.date_of_birth,
                p.sex,
                prov.provider_id AS author_provider_id,
                prov.given_name AS author_given_name,
                prov.family_name AS author_family_name,
                prov.provider_type,
                prov.department
            FROM reports r
            INNER JOIN imaging_studies s ON r.imaging_study_id = s.imaging_study_id
            INNER JOIN orders o ON s.order_id = o.order_id
            INNER JOIN patients p ON o.patient_id = p.patient_id
            LEFT JOIN order_procedures op ON o.order_id = op.order_id
            LEFT JOIN providers prov ON r.author_provider_id = prov.provider_id
            WHERE r.report_id = %s
            LIMIT 1
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (report_id,))
            result = cursor.fetchone()
            cursor.close()
            
        return result

    def list_providers(self, provider_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List providers, optionally filtered by provider type.
        
        Args:
            provider_types: Optional list of provider types to filter by (e.g., ['Radiologist'])
            
        Returns:
            List of provider dictionaries
        """
        filters = []
        params = []
        
        if provider_types:
            placeholders = ','.join(['%s'] * len(provider_types))
            filters.append(f"provider_type IN ({placeholders})")
            params.extend(provider_types)
        
        where_clause = " WHERE " + " AND ".join(filters) if filters else ""
        
        sql = f"""
            SELECT 
                provider_id,
                npi,
                given_name,
                family_name,
                provider_type,
                department,
                email,
                phone
            FROM providers
            {where_clause}
            ORDER BY family_name, given_name
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            results = cursor.fetchall()
            cursor.close()
            
        return results

    def create_report(
        self,
        imaging_study_id: int,
        report_number: str,
        report_text: str,
        impression: str,
        author_provider_id: Optional[int] = None,
        report_status: str = "Preliminary",
        report_datetime: Optional[str] = None
    ) -> int:
        """Create a new radiology report.
        
        Args:
            imaging_study_id: FK to imaging_studies
            report_number: Unique report identifier
            report_text: Full report findings/body
            impression: Report impression/conclusion
            author_provider_id: FK to providers (radiologist)
            report_status: One of: Preliminary, Final, Amended, Cancelled
            report_datetime: Report date/time (defaults to NOW)
            
        Returns:
            The new report_id
        """
        sql = """
            INSERT INTO reports (
                imaging_study_id,
                report_number,
                report_text,
                impression,
                author_provider_id,
                report_status,
                report_datetime
            ) VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()))
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                imaging_study_id,
                report_number,
                report_text,
                impression,
                author_provider_id,
                report_status,
                report_datetime
            ))
            report_id = cursor.lastrowid
            cursor.close()
            
        return report_id

    def update_report_dicom_ids(
        self,
        report_id: int,
        dicom_sop_instance_uid: str,
        dicom_series_instance_uid: str
    ) -> None:
        """Update report with DICOM identifiers after PDF attachment.
        
        Args:
            report_id: The report to update
            dicom_sop_instance_uid: SOP Instance UID of the encapsulated PDF
            dicom_series_instance_uid: Series Instance UID of the PDF series
        """
        sql = """
            UPDATE reports 
            SET dicom_sop_instance_uid = %s,
                dicom_series_instance_uid = %s
            WHERE report_id = %s
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (dicom_sop_instance_uid, dicom_series_instance_uid, report_id))
            cursor.close()

    def create_imaging_study(
        self,
        order_id: int,
        study_instance_uid: str,
        study_started: Optional[str] = None,
        study_completed: Optional[str] = None,
        status: str = "Available",
        number_of_series: Optional[int] = None,
        number_of_instances: Optional[int] = None,
        fhir_imaging_study_id: Optional[str] = None
    ) -> int:
        """Create a new imaging study record in the RIS.
        
        Args:
            order_id: FK to orders table
            study_instance_uid: DICOM Study Instance UID
            study_started: Study start datetime (ISO format or MySQL datetime)
            study_completed: Study completion datetime (ISO format or MySQL datetime)
            status: Study status (Registered, Available, Cancelled, EnteredInError)
            number_of_series: Number of series in the study
            number_of_instances: Total number of instances
            fhir_imaging_study_id: Optional FHIR ImagingStudy resource ID
            
        Returns:
            The new imaging_study_id
        """
        sql = """
            INSERT INTO imaging_studies (
                order_id,
                study_instance_uid,
                study_started,
                study_completed,
                status,
                number_of_series,
                number_of_instances,
                fhir_imaging_study_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                study_started = COALESCE(VALUES(study_started), study_started),
                study_completed = COALESCE(VALUES(study_completed), study_completed),
                status = VALUES(status),
                number_of_series = COALESCE(VALUES(number_of_series), number_of_series),
                number_of_instances = COALESCE(VALUES(number_of_instances), number_of_instances)
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                order_id,
                study_instance_uid,
                study_started,
                study_completed,
                status,
                number_of_series,
                number_of_instances,
                fhir_imaging_study_id
            ))
            # Get the ID (either new or existing)
            if cursor.lastrowid:
                imaging_study_id = cursor.lastrowid
            else:
                # If ON DUPLICATE KEY UPDATE was used, fetch the existing ID
                cursor.execute(
                    "SELECT imaging_study_id FROM imaging_studies WHERE study_instance_uid = %s",
                    (study_instance_uid,)
                )
                imaging_study_id = cursor.fetchone()[0]
            cursor.close()
            
        return imaging_study_id

