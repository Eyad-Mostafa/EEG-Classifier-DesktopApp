from app.db import get_session
from app.db.models import AnalysisMethod, PreprocessingMethod
from app.core.registry import get_all_algorithms


def seed_methods():
    db = get_session()

    try:
        all_steps = get_all_algorithms(detailed=True)

        analysis_methods = [
            step for step in all_steps if step.get("type") == "analysis"
        ]

        preprocessing_methods = [
            step for step in all_steps if step.get("type") == "preprocessing"
        ]

        added_analysis = 0
        updated_analysis = 0
        skipped_analysis = 0

        added_preprocessing = 0
        updated_preprocessing = 0
        skipped_preprocessing = 0

        # -------------------------------------------------
        # Analysis seeding
        # -------------------------------------------------
        for method in analysis_methods:
            method_name = (
                method.get("id") or method.get("method_id") or method.get("name")
            )

            description = method.get("description")

            if not method_name:
                continue

            existing = (
                db.query(AnalysisMethod)
                .filter(AnalysisMethod.method_name == method_name)
                .one_or_none()
            )

            # لو موجودة بالفعل
            if existing:

                # لو description فاضية وعندنا قيمة جديدة
                if not existing.description and description:
                    existing.description = description
                    updated_analysis += 1
                else:
                    skipped_analysis += 1

                continue

            # إضافة جديدة
            db.add(
                AnalysisMethod(
                    method_name=method_name,
                    description=description,
                )
            )

            added_analysis += 1

        # -------------------------------------------------
        # Preprocessing seeding
        # -------------------------------------------------
        for method in preprocessing_methods:
            method_name = (
                method.get("id") or method.get("method_id") or method.get("name")
            )

            description = method.get("description")

            if not method_name:
                continue

            existing = (
                db.query(PreprocessingMethod)
                .filter(PreprocessingMethod.method_name == method_name)
                .one_or_none()
            )

            # لو موجودة بالفعل
            if existing:

                # لو description فاضية وعندنا قيمة جديدة
                if not existing.description and description:
                    existing.description = description
                    updated_preprocessing += 1
                else:
                    skipped_preprocessing += 1

                continue

            # إضافة جديدة
            db.add(
                PreprocessingMethod(
                    method_name=method_name,
                    description=description,
                )
            )

            added_preprocessing += 1

        db.commit()

        print(
            f"\nSeed complete:\n"
            f"Analysis -> Added: {added_analysis}, "
            f"Updated: {updated_analysis}, "
            f"Skipped: {skipped_analysis}\n"
            f"Preprocessing -> Added: {added_preprocessing}, "
            f"Updated: {updated_preprocessing}, "
            f"Skipped: {skipped_preprocessing}"
        )

    except Exception as e:
        db.rollback()
        print(f"Error while seeding methods: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_methods()
