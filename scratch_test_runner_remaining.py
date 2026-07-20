import os
import sys
import re
import asyncio
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath("d:/ENGR/Scrutin"))

from app.memory.migrations import run_migrations
from app.utils.env_validator import validate_env
import app.tools._register_all  # noqa
from app.orchestrator.loop import run_orchestrator
from app.utils.logger import configure_terminal_logger

# Disable verbose logging to keep output clean
configure_terminal_logger(trace=False)

load_dotenv()
config = validate_env()
db_path = "scrutin_test_suite.db"

# Ensure migrations are run on the test suite db
run_migrations(db_path)

TEST_CASES_PATH = "d:/ENGR/Scrutin/Implementation/Test_Cases.md"

def parse_test_cases():
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    cases = []
    current_case = None

    # Matches:
    # 1. - [ ] **A2. "Eating raw garlic..."**
    # 2. **F1. "A satirical news..."** (without checklist prefix yet)
    # 3. - [x] **A1. "Drinking cow..."**
    case_re = re.compile(r'^(?:-\s+\[([ x])\]\s+)?\*\*([A-I]\d+)\.\s+"([^"]+)"\*\*')
    # Matches - Expected: **Verdict**
    for i, line in enumerate(lines):
        m_case = case_re.match(line.strip())
        if m_case:
            status = m_case.group(1)  # 'x', ' ', or None
            case_id = m_case.group(2)
            claim = m_case.group(3)
            
            current_case = {
                "id": case_id,
                "claim": claim,
                "line_idx": i,
                "original_line": line,
                "status": status,
                "expected": None
            }
            cases.append(current_case)
        elif current_case and line.strip().startswith("- Expected:"):
            exp_text = line.strip().split("- Expected:", 1)[1].strip()
            # Strip out bold and italic markdown tags
            exp_text = exp_text.replace("**", "").replace("*", "")
            current_case["expected"] = exp_text
            
    return cases, lines

def check_verdict_match(got: str, expected: str) -> bool:
    got = got.lower().strip()
    expected = expected.lower().strip()
    
    # Simple direct checks
    if got == expected:
        return True
        
    # Flexible substring/alternative checks
    if "unverifiable" in expected or "contested" in expected:
        if got in ("unverifiable", "inconclusive"):
            return True
            
    if "partially true" in expected:
        if got in ("partially true", "misleading"):
            return True
            
    if "/" in expected:
        parts = [p.strip() for p in expected.split("/")]
        if got in parts:
            return True
            
    if got in expected:
        return True
        
    return False

async def run_suite():
    cases, lines = parse_test_cases()
    
    # Filter only cases that are not completed ('x') and have a valid expected output
    remaining_cases = [c for c in cases if c["status"] != 'x' and c["expected"] is not None]
    
    print(f"Total parsed cases: {len(cases)}")
    print(f"Remaining cases to test: {len(remaining_cases)}")
    
    for idx, case in enumerate(remaining_cases):
        print(f"\n==================================================")
        print(f"[{idx+1}/{len(remaining_cases)}] Running Case {case['id']}: \"{case['claim'][:80]}...\"")
        print(f"Expected Verdict: {case['expected']}")
        
        # 10s cooldown between test cases to prevent Gemini RPM rate limit spikes
        if idx > 0:
            print("Cooldown for 10 seconds...")
            await asyncio.sleep(10)
            
        try:
            report = await run_orchestrator(
                raw_input=case["claim"],
                config=config,
                db_path=db_path,
            )
            got_verdict = report.overall_verdict
            passed = check_verdict_match(got_verdict, case["expected"])
            status = "PASS" if passed else "FAIL"
            print(f"Result: {status} | Got: {got_verdict} (Expected: {case['expected']})")
            
            # Update the markdown line in the lines list
            tick = "x" if passed else " "
            clean_line = case["original_line"].strip()
            # Strip existing checkboxes if any safely using regex
            clean_line = re.sub(r'^-\s+\[[ x]\]\s+', '', clean_line)
            
            lines[case["line_idx"]] = f"- [{tick}] {clean_line}\n"
            
            # Write back immediately after each case to save progress
            with open(TEST_CASES_PATH, "w", encoding="utf-8") as f:
                f.writelines(lines)
                
        except Exception as e:
            print(f"ERROR running case {case['id']}: {e}")
            clean_line = case["original_line"].strip()
            clean_line = re.sub(r'^-\s+\[[ x]\]\s+', '', clean_line)
            lines[case["line_idx"]] = f"- [ ] {clean_line}\n"
            with open(TEST_CASES_PATH, "w", encoding="utf-8") as f:
                f.writelines(lines)

if __name__ == "__main__":
    asyncio.run(run_suite())
