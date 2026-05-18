"""Authentication boundary notes for the submission deploy.

RoboQC v1 intentionally uses Cloud Run IAM + a service account at the platform
edge. There is no in-app API-key or OAuth middleware in the submission path.
"""
