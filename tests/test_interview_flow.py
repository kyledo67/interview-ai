import json
import subprocess
import sys
from datetime import datetime, timedelta
from test_vercel_migration import database, client
from app.models.interview import Interview
from app.api.endpoints import interviews, code
from app.api.endpoints.gemini import InterviewService
from app.main import app


def seed(db, count=1, minutes=0, mode="behavioral"):
    problem = InterviewService(None, "")._generate_technical_question("intern")
    problem["function_name"] = "is_valid"
    record = Interview(id=10, user_id=1, status="active", resume_path="test", transcript=[],
        meta_info={"candidate_level":"intern", "mode":mode, "questions_asked":count,
            "behavioral_start_time":(datetime.now()-timedelta(minutes=minutes)).isoformat(),
            "technical_start_time":datetime.now().isoformat(), "technical_question":problem})
    db.add(record); db.commit()
    return record


def test_five_replies_persist_and_switch(client, database, monkeypatch):
    seed(database)
    monkeypatch.setattr(interviews, "is_relevant", lambda *args: True)
    monkeypatch.setattr(InterviewService, "_call_gemini", lambda *args: "Test AI reply")
    for i in range(5):
        response=client.post("/interviews/10/message",json={"message":"My answer"})
        assert response.status_code==200, response.text
        assert response.json()["should_switch_mode"] == (i == 4)
        database.expire_all()
        record=database.get(Interview,10)
        assert len(record.transcript)==2*(i+1)
    assert record.meta_info["mode"]=="technical"
    assert client.get("/interviews/10/get-technical-problem").status_code==200
    # A later request must stay technical rather than restart behavioral.
    response=client.post("/interviews/10/message",json={"message":"Let me think"})
    assert response.status_code==200
    database.expire_all()
    assert database.get(Interview,10).meta_info["mode"]=="technical"


def test_timer_switch_without_answer_is_idempotent(client,database):
    seed(database,minutes=16)
    response=client.post("/interviews/10/phase")
    assert response.status_code==200 and response.json()["mode"]=="technical"
    first=response.json()["technical_data"]
    database.expire_all()
    second=client.post("/interviews/10/phase").json()
    assert second["changed"] is False and second["technical_data"]==first
    assert len(database.get(Interview,10).transcript)==1


def test_timer_does_not_skip_an_unanswered_fifth_question(client,database):
    seed(database,count=5,minutes=2)
    assert client.post("/interviews/10/phase").json()["mode"]=="behavioral"


def test_code_results_control_solved_state_and_feedback(client,database,monkeypatch):
    seed(database,mode="technical")
    async def sandbox(source,language,stdin):
        # This is a test-only runner for fixed test strings, never user input.
        result=subprocess.run([sys.executable,"-c",source],capture_output=True,text=True,timeout=3)
        return {"status":{"id":3 if result.returncode==0 else 11,"description":"Accepted" if result.returncode==0 else "Runtime Error"},"stdout":result.stdout,"stderr":result.stderr}
    monkeypatch.setattr(code,"run_submission",sandbox)
    bad="def is_valid(s): return True"
    good="def is_valid(s):\n    stack=[]\n    pairs={')':'(',']':'[','}':'{'}\n    for c in s:\n        if c in pairs:\n            if not stack or stack.pop()!=pairs[c]: return False\n        else: stack.append(c)\n    return not stack"
    for source,expected in [(bad,False),("def is_valid(s): pass",False),("def is_valid(s): raise ValueError('broken')",False),(good,True)]:
        response=client.post("/code/execute",json={"source_code":source,"language_id":71,"interview_id":10})
        assert response.status_code==200,response.text
        assert response.json()["problem_solved"]==expected
        database.expire_all()
        assert database.get(Interview,10).meta_info["technical_problem_solved"]==expected
    assert client.post("/interviews/10/execute-code",json={"code":"forged","output":"correct","status":"Accepted"}).status_code==400
    assert client.post("/interviews/10/phase").json()["mode"]=="candidate_questions"


def test_execution_requires_auth_and_active_technical_interview(client,database):
    seed(database)
    body={"source_code":"print(1)","language_id":71,"interview_id":10}
    assert client.post("/code/execute",json=body).status_code==400
    from app.core.security import get_current_user
    app.dependency_overrides.pop(get_current_user)
    assert client.post("/code/execute",json=body).status_code==401


def test_runner_errors_are_actionable(client,database,monkeypatch):
    seed(database,mode="technical")
    monkeypatch.setattr(code,"JUDGE0_API_KEY",None)
    r=client.post("/code/execute",json={"source_code":"def is_valid(s): pass","language_id":71,"interview_id":10})
    assert r.status_code==503 and "API key" in r.json()["detail"]


def test_javascript_harness_and_triplet_normalization():
    cases=code.CASES["three_sum"]
    source,stdin=code.prepare_submission("function three_sum(a) { return []; }",63,"three_sum",cases)
    result=subprocess.run(["node","-e",source],capture_output=True,text=True,timeout=3)
    assert result.returncode==0
    assert code.grade_results({"status":{"id":3},"stdout":result.stdout},"three_sum",cases)==(False,1)
    reordered=[[[1,0,-1],[2,-1,-1]],[[0,0,0]],[]]
    assert code.grade_results({"status":{"id":3},"stdout":json.dumps(reordered)},"three_sum",cases)==(True,3)
