# DB 存盘详细步骤

每章写完后，编排器需执行以下 DB 存盘操作。通用校验规则见 shared/db-save-protocol.md。

## 6.1.1 角色状态增量更新（character_increment）

每章写完后，必须用 `character_increment` 增量更新出场角色的状态：

```python
for character in involved_characters:
    character_increment(
        novel_name="NOVEL_NAME",
        character_name=character.name,
        snapshot_update=json.dumps({
            "identity": character.new_identity,
            "ability": character.new_ability_state,
            "goal": character.new_goal,
            "knows": character.new_knowledge,
            "doesnt_know": character.new_unknowns,
            "relationships": character.relationship_changes
        }),
        growth_add=json.dumps({
            "volume": current_volume,
            "chapter": chapter_number,
            "changes": character.changes_this_chapter,
            "trigger": character.trigger_event
        })
    )
```

## 6.1.2 角色快照（character_snapshot）

`character_increment` 写入 `characters.current_snapshot`（可变），但 `get_chapter_context` 和 `character_detail` 从 `character_state_snapshots` 表读取。必须同时写入快照表，下游才能读到数据：

```python
for character in involved_characters:
    character_snapshot(
        novel_name="NOVEL_NAME",
        character_name=character.name,
        chapter_number=chapter_number,
        location=character.current_location,
        arc_phase=character.arc_phase,
        emotional_state=character.emotional_state,
        physical_state=character.physical_state,
        ability_snapshot=json.dumps(character.ability_state),
        inventory_snapshot=json.dumps(character.inventory),
        knowledge_snapshot=json.dumps(character.knowledge_state),
        notes=character.snapshot_notes
    )
```

## 6.1.3 关系快照（relation_snapshot）

Creative Director 在创意蓝图中设计了关系变化。每章写完后，对有显著变化的角色关系调用快照：

```python
for relation_change in blueprint.relationship_changes:
    relation_snapshot(
        novel_name="NOVEL_NAME",
        from_name=relation_change.from_name,
        to_name=relation_change.to_name,
        chapter_number=chapter_number,
        intensity=relation_change.new_intensity,
        status=relation_change.new_status,  # active/broken/evolved/hidden
        notes=relation_change.description
    )
```

## 6.1.4 人物蒸馏演化记录（distillation_evolve）

每章写完后，对**有显著演化**的角色（决策变化/信念转变/能力解锁/弧线推进/关键抉择），记录蒸馏模型增量：

```python
for character in characters_with_evolution:
    if not character.distillation_tracked:
        continue  # 跳过已关闭蒸馏追踪的角色（临时NPC）
    distillation_evolve(
        novel_name="NOVEL_NAME",
        character_name=character.name,
        chapter_number=chapter_number,
        decision_delta=json.dumps(character.decision_changes),
        new_knowledge=json.dumps(character.new_information),
        changed_beliefs=json.dumps(character.belief_shifts),
        relation_shifts=json.dumps(character.relation_shifts),
        voice_changes=json.dumps(character.voice_changes),
        ability_changes=json.dumps(character.ability_changes),
        arc_transition=json.dumps(character.arc_transition),
        key_decision=json.dumps(character.key_decision),
        notes=character.evolution_notes
    )
```

主角色（`distillation_tracked=1`）应每次写完后都调（持续追踪弧线推进），配角只在有显著变化时调（避免噪音）。临时NPC（`distillation_tracked=0`）会被上述 `if not character.distillation_tracked: continue` 自动跳过。
