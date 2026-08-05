import argparse
import asyncio
import json
from pathlib import Path

from app.db.session import async_session_maker
from app.repositories.meta_operations import MetaOperationsRepository


DEFAULT_SEED = Path("resources/meta_operations/groups_seed.json")


async def run(seed_path: Path, *, apply: bool) -> None:
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    groups = payload.get("groups")
    if payload.get("schema_version") != 1 or not isinstance(groups, list):
        raise ValueError("unsupported groups seed format")

    created = 0
    updated = 0
    async with async_session_maker() as session:
        repo = MetaOperationsRepository(session)
        for values in groups:
            existing = await repo.get_group_by_external_id(
                values["external_id"],
                platform=values.get("platform", "facebook"),
            )
            if not apply:
                if existing is None:
                    created += 1
                else:
                    updated += 1
                continue
            import_values = dict(values)
            if existing is not None:
                import_values["enabled"] = existing.enabled
            _, was_created = await repo.upsert_group(import_values)
            created += int(was_created)
            updated += int(not was_created)
        if apply:
            await session.commit()
        enabled_count = len(await repo.list_groups(enabled=True, limit=100_000))

    mode = "APPLY" if apply else "DRY_RUN"
    print(
        f"META_GROUP_IMPORT_{mode}_OK total={len(groups)} "
        f"created={created} updated={updated} enabled={enabled_count}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import the normalized Meta Operations group registry."
    )
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.seed, apply=args.apply))


if __name__ == "__main__":
    main()
