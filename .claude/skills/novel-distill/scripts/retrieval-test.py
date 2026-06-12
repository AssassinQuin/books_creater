#!/usr/bin/env python3
"""检索精度回归测试（v6.0）。
对 project_relevance.{active_project}.score >= 4 的高优 borrowable，
跑 evals/retrieval-cases.json 的三类测试（should_trigger / should_not_trigger / edge_case）。

用法:
  python3 retrieval-test.py <work_name> [--active-project <project>] [--eval-file <path>]

通过标准: should_trigger >= 80% AND should_not_trigger == 100%（诱饵容错为 0）。

注意：本脚本仅做静态字段检查（trigger_signals 与 test_cases 的 language_signals 匹配度）。
真实的语义级检索精度需要主 agent 调用 ctx_search/search 后人工判定，本脚本提供的是
schema 层面的回归——确保 trigger_signals 字段与 test_cases 设计一致。
"""
import json, sys, os, argparse, glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_EVAL_FILE = os.path.join(SKILL_DIR, "evals", "retrieval-cases.json")
DEFAULT_DB_DIR = os.path.join(os.getcwd(), "novels", "_参考库")

def load_borrowables(work_name, db_dir):
    work_dir = os.path.join(db_dir, work_name, ".distill-tmp")
    if not os.path.isdir(work_dir):
        print(f"[ERR] 作品目录不存在: {work_dir}")
        return []
    borrowables = []
    for f in sorted(glob.glob(os.path.join(work_dir, "*.json"))):
        if "rejected" in f:
            continue
        try:
            with open(f) as fp:
                data = json.load(fp)
            for b in data.get("borrowable", []):
                if isinstance(b, dict):
                    borrowables.append(b)
        except (json.JSONDecodeError, IOError):
            continue
    return borrowables

def filter_high_priority(borrowables, active_project):
    if not active_project:
        return borrowables
    high = []
    for b in borrowables:
        pr = b.get("project_relevance", {})
        info = pr.get(active_project, {})
        if info.get("score", 0) >= 4:
            high.append(b)
    return high

def signal_match(borrowable, test_case):
    """静态匹配：test_case.language_signals_expected 是否出现在 borrowable.trigger_signals 中"""
    ts = borrowable.get("trigger_signals", [])
    if not ts:
        return False
    expected = test_case.get("language_signals_expected", [])
    if not expected:
        return None
    ts_lower = [s.lower() for s in ts if isinstance(s, str)]
    for sig in expected:
        if any(sig.lower() in t for t in ts_lower):
            return True
    return False

def run_tests(high_priority, eval_cases):
    results = {"should_trigger": [], "should_not_trigger": [], "edge_case": []}
    for tc in eval_cases:
        ttype = tc.get("type")
        if ttype not in results:
            continue
        matched = False
        for b in high_priority:
            if signal_match(b, tc):
                matched = True
                break
        results[ttype].append({"id": tc.get("id"), "matched": matched, "prompt": tc.get("prompt")[:50]})

    summary = {}
    for ttype, items in results.items():
        if not items:
            summary[ttype] = None
            continue
        passed = sum(1 for x in items if x["matched"])
        summary[ttype] = {
            "total": len(items),
            "passed": passed,
            "rate": passed / len(items) if items else 0
        }
    return summary, results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("work_name")
    parser.add_argument("--active-project", default=None)
    parser.add_argument("--eval-file", default=DEFAULT_EVAL_FILE)
    parser.add_argument("--db-dir", default=DEFAULT_DB_DIR)
    args = parser.parse_args()

    if not os.path.isfile(args.eval_file):
        print(f"[ERR] eval 文件不存在: {args.eval_file}")
        sys.exit(1)

    with open(args.eval_file) as f:
        eval_data = json.load(f)
    eval_cases = eval_data.get("test_cases", [])

    borrowables = load_borrowables(args.work_name, args.db_dir)
    if not borrowables:
        print(f"[ERR] 作品 {args.work_name} 无 borrowable 数据")
        sys.exit(1)

    high = filter_high_priority(borrowables, args.active_project)
    print(f"高优 borrowable: {len(high)} 条 (project={args.active_project or 'all'}, score>=4)")
    print(f"测试用例: {len(eval_cases)} 条\n")

    summary, details = run_tests(high, eval_cases)

    print("=" * 50)
    print("检索精度回归结果")
    print("=" * 50)
    for ttype, s in summary.items():
        if s is None:
            print(f"  {ttype}: 无用例")
        else:
            emoji = "✓" if s["rate"] >= 0.8 else "✗"
            print(f"  {emoji} {ttype}: {s['passed']}/{s['total']} = {s['rate']*100:.0f}%")

    pass_criteria = eval_data.get("_pass_criteria", {})
    st_min = pass_criteria.get("should_trigger_min", 0.8)
    snt_min = pass_criteria.get("should_not_trigger_min", 1.0)

    st_ok = summary["should_trigger"] and summary["should_trigger"]["rate"] >= st_min
    snt_ok = summary["should_not_trigger"] and summary["should_not_trigger"]["rate"] >= snt_min

    print()
    if st_ok and snt_ok:
        print(f"✓ PASS: should_trigger >= {st_min*100:.0f}% AND should_not_trigger >= {snt_min*100:.0f}%")
        sys.exit(0)
    else:
        print(f"✗ FAIL: should_trigger {'OK' if st_ok else 'FAIL'} / should_not_trigger {'OK' if snt_ok else 'FAIL'}")
        print("  未通过 → 检查 trigger_signals 字段，而非修测试用例")
        for ttype, items in details.items():
            for item in items:
                if not item["matched"]:
                    print(f"    - [{ttype}] {item['id']}: {item['prompt']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
