"""
Script de migração: Sincroniza raw_card_data → player_cards
=============================================================
Preenche os campos do PlayerCard que estão vazios (overall=0, position=None, etc.)
com dados que já existem no raw_card_data JSON da tabela sbc_sets.

Uso: python -m backend.scripts.sync_raw_to_player_cards
"""

import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_migration")

# Mapeamento de stats da listagem para colunas do PlayerCard
STAT_MAP = {
    "PAC": "pace", "SHO": "shooting", "PAS": "passing",
    "DRI": "dribbling_stat", "DEF": "defending", "PHY": "physic",
}


async def run():
    from backend.core.database import get_session, init_db
    from backend.models.models import SBCSet, PlayerCard
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    await init_db()

    async with get_session() as db:
        result = await db.execute(
            select(SBCSet)
            .options(selectinload(SBCSet.player_card))
            .where(SBCSet.raw_card_data.isnot(None))
        )
        sbc_sets = result.scalars().all()

        updated = 0
        created = 0

        for sbc in sbc_sets:
            try:
                raw = json.loads(sbc.raw_card_data)
            except (json.JSONDecodeError, TypeError):
                continue

            pc = sbc.player_card

            # Se não existe player_card, criar
            if not pc:
                pc = PlayerCard(
                    sbc_set_id=sbc.id,
                    name=raw.get("name") or sbc.name,
                    overall=int(raw.get("rating") or 0),
                )
                db.add(pc)
                created += 1
            
            # ── Sincronizar campos do raw → player_card ──
            changed = False

            # Overall e Position
            if pc.overall == 0 and raw.get("rating"):
                try:
                    pc.overall = int(raw["rating"])
                    changed = True
                except (ValueError, TypeError):
                    pass
            if not pc.position and raw.get("position"):
                pc.position = raw["position"]
                changed = True

            # Face stats
            for stat_entry in raw.get("stats", []):
                col = STAT_MAP.get(stat_entry.get("name", "").upper())
                if col and getattr(pc, col, None) is None:
                    try:
                        setattr(pc, col, int(stat_entry["value"]))
                        changed = True
                    except (ValueError, TypeError):
                        pass

            # SM / WF
            if not pc.skill_moves and raw.get("skill_moves"):
                try:
                    pc.skill_moves = int(raw["skill_moves"])
                    changed = True
                except (ValueError, TypeError):
                    pass
            if not pc.weak_foot and raw.get("weak_foot"):
                try:
                    pc.weak_foot = int(raw["weak_foot"])
                    changed = True
                except (ValueError, TypeError):
                    pass

            # URLs visuais
            url_map = {
                "bg_url": "card_image_url",
                "bg_url_hd": "card_image_url",  # HD sobrescreve baixa res
                "face_url": "face_url",
                "face_url_hd": "render_url",
                "nation_url": "nation_flag_url",
                "club_url": "club_logo_url",
                "league_url": "league_logo_url",
            }
            for raw_key, pc_field in url_map.items():
                if raw.get(raw_key) and not getattr(pc, pc_field, None):
                    setattr(pc, pc_field, raw[raw_key])
                    changed = True
            # HD URLs sobrescrevem independente de já ter valor
            if raw.get("bg_url_hd"):
                pc.card_image_url = raw["bg_url_hd"]
                changed = True
            if raw.get("face_url_hd"):
                pc.render_url = raw["face_url_hd"]
                changed = True

            # Playstyles
            if not pc.playstyles_json and raw.get("playstyles"):
                pc.playstyles_json = json.dumps(raw["playstyles"])
                changed = True

            # Alt positions / workrates
            if not pc.alt_positions and raw.get("alt_positions"):
                pc.alt_positions = raw["alt_positions"]
                changed = True
            if not pc.workrates and raw.get("workrates"):
                pc.workrates = raw["workrates"]
                changed = True

            if changed:
                updated += 1

        await db.commit()
        logger.info(f"✅ Migração concluída: {created} criados, {updated} atualizados de {len(sbc_sets)} SBCs")


if __name__ == "__main__":
    asyncio.run(run())
