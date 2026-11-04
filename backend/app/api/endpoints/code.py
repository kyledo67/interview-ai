"""Authenticated execution and server-side correctness checks."""
import asyncio
import hashlib
import json
import os
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.interview import Interview

router = APIRouter(prefix="/code")
JUDGE0_URL = os.getenv("JUDGE0_URL", "https://judge0-ce.p.rapidapi.com/submissions").rstrip("/")
JUDGE0_API_KEY = os.getenv("JUDGE0_API_KEY")

# Arguments and expected return values. These belong to the server, not the client.
CASES = {
    "three_sum": [([[-1,0,1,2,-1,-4]], [[-1,-1,2],[-1,0,1]]), ([[0,0,0,0]], [[0,0,0]]), ([[0,1,1]], [])],
    "max_area": [([[1,8,6,2,5,4,8,3,7]],49), ([[1,1]],1), ([[4,3,2,1,4]],16)],
    "length_of_longest_substring": [(["abcabcbb"],3), (["bbbbb"],1), ([""],0), (["pwwkew"],3)],
    "product_except_self": [([[1,2,3,4]],[24,12,8,6]), ([[-1,1,0,-3,3]],[0,0,9,0,0]), ([[0,0]],[0,0])],
    "is_valid": [(["()"],True), (["()[]{}"],True), (["(]"],False), (["([)]"],False), (["{[]}"],True)],
    "trap": [([[0,1,0,2,1,0,1,3,2,1,2,1]],6), ([[4,2,0,3,2,5]],9), ([[1,2,3]],0)],
    "merge_k_lists": [([[[1,4,5],[1,3,4],[2,6]]],[1,1,2,3,4,4,5,6]), ([[]],[]), ([[[]]],[])],
    "min_window": [(["ADOBECODEBANC","ABC"],"BANC"), (["a","a"],"a"), (["a","aa"],"")],
    "ladder_length": [(["hit","cog",["hot","dot","dog","lot","log","cog"]],5), (["hit","cog",["hot","dot","dog","lot","log"]],0), (["a","c",["a","b","c"]],2)],
}

class ExecutionRequest(BaseModel):
    source_code: str = Field(min_length=1, max_length=60000)
    language_id: int
    interview_id: int
    stdin: str = ""


def prepare_submission(source, language, function, cases):
    args = [case[0] for case in cases]
    if language == 71:
        # Run untrusted code only inside Judge0. Redirect example/debug prints.
        source = "import json as _json, contextlib as _contextlib, io as _io\nwith _contextlib.redirect_stdout(_io.StringIO()):\n" + "\n".join("    " + line for line in source.splitlines())
        source += f"\n_results = []\nfor _args in _json.loads({json.dumps(args)!r}):\n    with _contextlib.redirect_stdout(_io.StringIO()):\n        _value = {function}(*_args)\n    _results.append(_value)\nprint(_json.dumps(_results))"
    elif language == 63:
        source = "const _log = console.log; console.log = () => {};\n" + source
        source += f"\nconsole.log = _log; console.log(JSON.stringify({json.dumps(args)}.map(args => {function}(...args))));"
    # Java/C++ standalone programs receive a JSON array of argument lists on
    # stdin and must print a JSON array of return values, one per test case.
    return source, json.dumps(args)


def grade_results(result, function, cases):
    if result.get("status", {}).get("id") != 3:
        return False, 0
    try:
        actual = json.loads((result.get("stdout") or "").strip().splitlines()[-1])
        if not isinstance(actual, list) or len(actual) != len(cases):
            return False, 0
        expected = [case[1] for case in cases]
        if function == "three_sum":
            actual = [sorted(sorted(t) for t in answer) for answer in actual]
            expected = [sorted(sorted(t) for t in answer) for answer in expected]
        passed = sum(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True) for a,b in zip(actual, expected))
        return passed == len(cases), passed
    except (ValueError, TypeError, IndexError):
        return False, 0


def verified_checks(result, function, cases):
    try:
        actual = json.loads((result.get("stdout") or "").strip().splitlines()[-1])
        if not isinstance(actual, list) or len(actual) != len(cases):
            actual = [None] * len(cases)
    except (ValueError, IndexError):
        actual = [None] * len(cases)
    checks = []
    for index, (args, expected) in enumerate(cases):
        passed, _ = grade_results({"status": result.get("status", {}), "stdout": json.dumps([actual[index]])}, function, [(args, expected)])
        checks.append({"arguments":args, "expected":expected, "passed":passed})
    return checks


async def run_submission(source, language, stdin):
    if not JUDGE0_API_KEY:
        raise HTTPException(status_code=503, detail="Code runner API key is missing.")
    headers = {"X-RapidAPI-Host": "judge0-ce.p.rapidapi.com", "X-RapidAPI-Key": JUDGE0_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(JUDGE0_URL, params={"base64_encoded":"false", "wait":"false"}, headers=headers,
                json={"source_code":source, "language_id":language, "stdin":stdin, "cpu_time_limit":3, "wall_time_limit":8})
            response.raise_for_status()
            result = response.json()
            for _ in range(30):
                if result.get("status", {}).get("id", 1) not in (1, 2):
                    return result
                token = result.get("token")
                if not token:
                    raise HTTPException(status_code=502, detail="Code runner returned no submission token.")
                await asyncio.sleep(0.5)
                response = await client.get(f"{JUDGE0_URL}/{token}", params={"base64_encoded":"false"}, headers=headers)
                response.raise_for_status()
                result = response.json()
            raise HTTPException(status_code=504, detail="Code runner timed out. Please try again.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Code runner rejected the request (HTTP {exc.response.status_code}). Check the Judge0 subscription and quota.")
    except (httpx.RequestError, ValueError):
        raise HTTPException(status_code=502, detail="Code runner is unavailable. Please try again.")


@router.post("/execute")
async def execute_code(payload: ExecutionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.language_id not in (71,63,62,54):
        raise HTTPException(status_code=400, detail="Unsupported language.")
    interview = db.query(Interview).filter(Interview.id == payload.interview_id, Interview.user_id == user.id, Interview.status == "active").with_for_update().first()
    if interview is None:
        raise HTTPException(status_code=404, detail="Active interview not found")
    if interview.meta_info.get("mode") != "technical":
        raise HTTPException(status_code=400, detail="Interview is not in technical phase")
    function = (interview.meta_info.get("technical_question") or {}).get("function_name")
    cases = CASES.get(function)
    if not cases:
        raise HTTPException(status_code=400, detail="No test cases available for this problem.")
    source, stdin = prepare_submission(payload.source_code, payload.language_id, function, cases)
    result = await run_submission(source, payload.language_id, stdin)
    solved, passed = grade_results(result, function, cases)
    status = result.get("status", {}).get("description", "Execution failed")
    if result.get("status", {}).get("id") == 3:
        status = "Accepted" if solved else "Wrong Answer"
    output = f"{passed}/{len(cases)} test cases passed.\n" + (result.get("stdout") or result.get("stderr") or result.get("compile_output") or "No output received")
    interview.meta_info["current_code"] = payload.source_code
    interview.meta_info["language_id"] = payload.language_id
    interview.meta_info["technical_problem_solved"] = solved
    interview.meta_info["last_execution"] = {"code_hash":hashlib.sha256(payload.source_code.encode()).hexdigest(), "status":status, "output":output[:16000], "passed":passed, "total":len(cases), "language_id":payload.language_id, "checks":verified_checks(result, function, cases)}
    db.commit()
    return {**result, "status":{"id":(3 if solved else 4) if result.get("status", {}).get("id") == 3 else result.get("status", {}).get("id", 13), "description":status}, "output":output, "problem_solved":solved, "passed":passed, "total":len(cases)}
