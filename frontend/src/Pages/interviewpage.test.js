import React from 'react';
import {render, screen, fireEvent, waitFor, act} from '@testing-library/react';
jest.mock('react-router-dom', () => ({useNavigate: () => jest.fn()}), {virtual:true});
import InterviewPage from './interviewpage';

jest.mock('@monaco-editor/react', () => function MockEditor({value,onChange}) {
  return <textarea aria-label="Code editor" value={value} onChange={e=>onChange(e.target.value)} />;
});

const problem={title:'Valid Parentheses',difficulty:'Easy',description:'Return whether brackets are balanced.',starter_code:'def is_valid(s): pass',function_name:'is_valid'};

test('timer opens technical editor and Run Code displays server grading', async () => {
  jest.useFakeTimers();
  const originalFetch=global.fetch;
  const errors=jest.spyOn(console,'error').mockImplementation(()=>{});
  let phaseChecks=0;
  global.fetch=jest.fn(async (url,options) => {
    let data;
    if(url==='/interviews/start') data={interview_id:10,candidate_level:'intern',ai_message:'Welcome'};
    else if(url==='/interviews/10/phase') data=++phaseChecks===1 ? {mode:'behavioral',changed:false} : {mode:'technical',changed:true,technical_data:problem,ai_response:'Coding time'};
    else if(url==='/interviews/10/context') data={updated:true};
    else if(url==='/code/execute') data={output:'0/5 test cases passed. Wrong answer',status:{description:'Wrong Answer'},problem_solved:false};
    else if(url==='/interviews/10/execute-code') data={feedback:'Check mismatched brackets.'};
    else return {ok:false,json:async()=>({detail:'TTS disabled in tests'})};
    return {ok:true,json:async()=>data};
  });
  try {
    render(<InterviewPage />);
    await act(async()=>{});
    expect(screen.queryByText('Run Code')).not.toBeInTheDocument();
    await act(async()=>{jest.advanceTimersByTime(10000);});
    expect(await screen.findByText('Valid Parentheses')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Code editor'),{target:{value:'def is_valid(s): return True'}});
    await act(async()=>{jest.advanceTimersByTime(1500);});
    const sync=global.fetch.mock.calls.find(([url])=>url==='/interviews/10/context');
    expect(JSON.parse(sync[1].body)).toMatchObject({current_code:'def is_valid(s): return True',language_id:71});
    fireEvent.click(screen.getByText('Run Code'));
    await waitFor(()=>expect(screen.getByText('0/5 test cases passed. Wrong answer')).toBeInTheDocument());
    const call=global.fetch.mock.calls.find(([url])=>url==='/code/execute');
    expect(JSON.parse(call[1].body)).toMatchObject({interview_id:10,language_id:71,source_code:'def is_valid(s): return True'});
    expect(global.fetch.mock.calls.filter(([url])=>url==='/interviews/start')).toHaveLength(1);
  } finally {
    global.fetch=originalFetch;
    errors.mockRestore();
    jest.useRealTimers();
  }
});
