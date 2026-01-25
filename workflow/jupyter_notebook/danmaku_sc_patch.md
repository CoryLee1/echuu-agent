# SC 响应优化补丁

## 需要修改的位置

### 1. DanmakuEvaluator.evaluate() - 提高SC优先级

**原代码（Cell 17，line 829-840）：**
```python
# 3. SC加成
if danmaku.is_sc:
    if danmaku.amount >= 200:
        sc_bonus = 0.7
    elif danmaku.amount >= 100:
        sc_bonus = 0.5
    elif danmaku.amount >= 50:
        sc_bonus = 0.3
    else:
        sc_bonus = 0.2
else:
    sc_bonus = 0.0

danmaku.priority = base + relevance_bonus + sc_bonus
```

**修改为：**
```python
# 3. SC加成（大幅提升，确保SC能打断）
if danmaku.is_sc:
    if danmaku.amount >= 200:
        sc_bonus = 1.0  # 保证能打断任何阶段
    elif danmaku.amount >= 100:
        sc_bonus = 0.8  # 能打断大部分
    elif danmaku.amount >= 50:
        sc_bonus = 0.6  # 能打断中低cost
    else:
        sc_bonus = 0.4  # 小额SC也要重视
    
    # 🔥 SC特权：即使相关性低，也给保底bonus
    if relevance < 0.3 and sc_bonus >= 0.4:
        relevance_bonus = max(relevance_bonus, 0.2)  # SC至少有0.2相关性bonus
else:
    sc_bonus = 0.0

danmaku.priority = base + relevance_bonus + sc_bonus
```

---

### 2. PerformerV2._handle_danmaku_response() - 积极响应SC（已修改✅）

**已在 Cell 25 中修改，不需要再改。**

---

## 修改说明

1. **SC优先级提升**：
   - ¥200+: 1.0（之前0.7）- 保证能打断任何阶段
   - ¥100: 0.8（之前0.5）
   - ¥50: 0.6（之前0.3）
   - 其他SC: 0.4（之前0.2）

2. **SC特权逻辑**：
   - 即使弹幕与话题相关性低（< 0.3），SC也能获得0.2的保底相关性bonus
   - 这确保了SC总优先级 >= 0.3（base） + 0.2（保底relevance） + 0.4（最小sc_bonus） = 0.9
   - 0.9 的优先级可以打断大部分阶段（除了最高潮的 cost=0.95）

3. **improvise 响应优化**（已完成）：
   - SC：热情感谢 + 尝试关联话题 + 允许跑题
   - 普通弹幕：也积极回应，不再说"不在话题里"

## 预期效果

- ¥50 SC 的总优先级：0.3（base） + 0.2（保底） + 0.6（sc） = **1.1**
  - 可以打断除了最高潮（cost=0.9-0.95）之外的所有阶段

- ¥100 SC 的总优先级：0.3 + 0.2 + 0.8 = **1.3**
  - 可以打断任何阶段

- 即使是低相关的SC，主播也会：
  1. 热情感谢
  2. 尝试关联到当前话题
  3. 允许短暂跑题
  4. 自然过渡回主线


