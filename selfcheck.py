# -*- coding: utf-8 -*-
"""蜂蜜挂机 RPG · 无头自检（不开 tkinter 窗口）。

    python selfcheck.py

本仓 .venv 里没有 scipy（音频合成才开始用），而 ``src/sim_core/engine.py``
顶层就 import ``audio_service -> audio_engine -> scipy.io.wavfile``，
所以本自检不构造 SimCore，只验证与 GUI / 音频无关的纯逻辑层：

* ``src/sim_core/models/character.py``        —— 角色创建、升级、伤害/治疗钳制、存读往返
* ``src/sim_core/services/difficulty_service.py`` —— DDA 难度曲线、敌人缩放、反馈回路

这两层是挂机推进的核心：时间推进带来的经验/等级，以及 DDA 的难度与回血抑制。
输出保持 ASCII，避免 Windows 控制台代码页差异把中文打成乱码。
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)                      # json_pool 按项目根解析 data/*.json
sys.path.insert(0, str(ROOT))

from src.sim_core.models.character import (  # noqa: E402
    Character, CharClass, Race, init_race_class_config,
)
from src.sim_core.services.data_service import DataService  # noqa: E402
from src.sim_core.services.difficulty_service import DifficultyService  # noqa: E402


def _boot_registries() -> None:
    """按项目自身的数据源装配种族/职业/技能表。"""
    init_race_class_config(DataService())


def _make(name: str = "SelfCheck", seed: int = 20261026) -> Character:
    _boot_registries()
    return Character.create(name, Race.HUMAN, CharClass.WARRIOR, seed=seed)


# --------------------------------------------------------------------- 检查项
def check_character_progression() -> str:
    """同 seed 同角色；经验推进到升级；伤害/治疗不会越界。"""
    first = _make(seed=99)
    second = _make(seed=99)
    assert first.to_dict() == second.to_dict(), "same seed produced different characters"
    assert len(first.skills) > 0, "no skills assigned (skill table not loaded)"
    assert first.hp == first.max_hp, "new character does not start at full hp"

    level_before = first.level
    hp_before = first.max_hp
    for _ in range(20):
        first.gain_exp(120)
    assert first.level > level_before, f"exp did not advance level ({first.level})"
    assert first.max_hp >= hp_before, "max_hp shrank after level up"
    assert 0 <= first.hp <= first.max_hp, "hp escaped [0, max_hp]"

    dealt = first.take_damage(7)
    assert dealt > 0, "take_damage dealt nothing"
    assert first.hp < first.max_hp, "hp did not drop after damage"
    healed = first.heal(10_000)
    assert healed > 0 and first.hp == first.max_hp, "heal did not clamp at max_hp"

    return (f"character Lv{level_before}->Lv{first.level}, max_hp {hp_before:.0f}->"
            f"{first.max_hp:.0f}, damage/heal clamped")


def check_character_roundtrip() -> str:
    """角色存档 to_dict -> from_dict -> to_dict 必须完全一致（存档字段不丢）。"""
    char = _make("RoundTrip", seed=7)
    char.gain_exp(900)
    snapshot = char.to_dict()
    restored = Character.from_dict(snapshot)
    assert restored.to_dict() == snapshot, "character save/load round-trip changed data"
    assert restored.name == char.name
    assert restored.level == char.level
    assert restored.max_hp == char.max_hp
    assert restored.exp == char.exp
    assert restored.char_class.name == char.char_class.name
    return f"character save/load round-trip ({len(snapshot)} fields, Lv{char.level})"


class _Member:
    def __init__(self, level: int) -> None:
        self.level = level
        self.hp = 100


class _Party:
    """难度服务只用到 level / get_alive 这两个接口。"""

    def __init__(self, level: int) -> None:
        self.members = [_Member(level)]

    def get_alive(self):
        return [m for m in self.members if m.hp > 0]


def check_dda_curve() -> str:
    """DDA：新手保护、难度单调、敌人随队伍等级变强、战败触发回血抑制。"""
    dda = DifficultyService()
    assert dda._difficulty(1) == 0.0, "newbie zone should have zero difficulty"
    curve = [dda._difficulty(lv) for lv in (1, 5, 10, 20, 50)]
    assert all(a < b for a, b in zip(curve, curve[1:])), f"difficulty not monotonic: {curve}"

    dda.update_player_level(1)
    assert dda.dda_level == 0 and dda.get_enemy_attribute_multiplier() == 1.0
    dda.update_player_level(30)
    assert dda.dda_level > 0, "dda_level did not rise with player level"
    assert dda.get_enemy_attribute_multiplier() > 1.0, "enemies not scaled up"
    assert dda.get_reward_multiplier() < 1.0, "rewards not scaled down at high difficulty"

    template = {"name": "Slime", "hp": 30, "damage": 5, "defense": 2,
                "exp": 10, "gold": 5, "tags": [], "attack_interval": 2.0}
    random.seed(3)
    low = dda.scale_enemy_template(dict(template), _Party(5))
    random.seed(3)
    high = dda.scale_enemy_template(dict(template), _Party(30))
    assert high["hp"] > low["hp"], f"enemy hp did not scale: {low['hp']} -> {high['hp']}"
    assert high["level"] > low["level"], "enemy level did not follow party level"

    # 反馈回路：战败上报后回血抑制必须从 0 抬起来，并给出提示
    feedback = DifficultyService()
    assert feedback.regen_suppression == 0.0 and feedback.get_feedback_status()["history_count"] == 0
    feedback.on_combat_end(30.0, False, total_damage=50, enemy_max_hp=200, enemy_regen=5.0)
    status = feedback.get_feedback_status()
    assert status["history_count"] == 1, "combat result not recorded"
    assert feedback.regen_suppression > 0.0, "no regen suppression after defeat"
    assert feedback.feedback_hint, "no feedback hint after defeat"

    return (f"DDA curve D(1)=0..D(50)={curve[-1]:.1f}, enemy hp {low['hp']}->{high['hp']} "
            f"Lv5->Lv30, regen suppression 0->{feedback.regen_suppression:.2f}")


# --------------------------------------------------------------------- 入口
def main() -> int:
    checks = [
        ("character progression", check_character_progression),
        ("character save/load", check_character_roundtrip),
        ("DDA difficulty", check_dda_curve),
    ]
    passed: list[str] = []
    for name, fn in checks:
        try:
            passed.append(fn())
        except Exception as exc:  # noqa: BLE001
            print(f"selfcheck FAIL: {name} -> {type(exc).__name__}: {exc}")
            return 1
    print("selfcheck ok: " + "; ".join(passed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
