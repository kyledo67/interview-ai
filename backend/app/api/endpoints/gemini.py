import json
import re
from typing import Dict, Optional, List
import random
from google import genai

class InterviewService:
    def __init__(self, client, model_name: str):
        self.client = client
        self.model_name = model_name
        self.uploaded_resume_file = None
    
    def parse_resume_from_pdf(self, pdf_path: str) -> Dict:
        try:
            
            self.uploaded_resume_file = self.client.files.upload(file=pdf_path)
            
           
            analysis_prompt = """Analyze this software engineering resume thoroughly and extract the following information:

1. **Graduation Date**: Expected graduation date (format: Month Year, e.g., "May 2025")
2. **Experience Level**: Determine if this is:
   - "intern" level (freshman, sophomore, or junior year student)
   - "new_grad" level (senior year student or recent graduate)
3. **Non-Traditional Background**: Assess if this candidate has a non-traditional background for SWE:
   - Look for: non-CS degree (biology, business, medicine, humanities, etc.)
   - Minimal/no CS coursework
   - Work experience primarily in non-tech fields
   - Career switcher indicators (bootcamp, self-taught, pivoting from another industry)
   - Return TRUE if they appear non-traditional, FALSE if traditional CS background
4. **Background Context**: If non-traditional, briefly note their primary background (e.g., "medical background", "business major", "liberal arts with self-taught coding")
5. **Education**: University name, degree, major, GPA (if listed), relevant coursework
6. **Work Experience**: All internships, jobs, and relevant work experience with descriptions
7. **Projects**: Technical projects with descriptions and technologies used
8. **Skills**: Programming languages, frameworks, tools, and technologies
9. **Activities**: Leadership roles, clubs, extracurriculars (if any)
10. **Overall Assessment**: Based on this resume, assess:
   - Technical strength (1-10)
   - Project complexity (1-10)
   - Overall preparedness for software engineering role

Return your analysis in this EXACT JSON format:
{
  "graduation_date": "Month Year or Unknown",
  "level": "intern or new_grad",
  "is_non_traditional": true or false,
  "background_context": "brief description if non-traditional, else empty string",
  "education": "detailed education info",
  "experience": "detailed work experience",
  "projects": "detailed projects",
  "skills": ["skill1", "skill2", ...],
  "activities": "clubs and leadership",
  "raw_assessment": "brief overall assessment of candidate strength",
  "technical_strength": 1-10,
  "project_complexity": 1-10
}

Be thorough and extract as much relevant information as possible. For the level determination:
- If graduation is within current academic year or already graduated: "new_grad"
- If graduation is 1+ years away: "intern"
- If unclear, look for year indicators (Freshman/Sophomore/Junior = "intern", Senior = "new_grad")
- Non-traditional candidates default to "intern" level regardless of graduation"""
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[analysis_prompt, self.uploaded_resume_file]
            )
            
            response_text = response.text.strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                resume_data = json.loads(json_match.group())
            else:
                resume_data = json.loads(response_text)
            
            resume_data.setdefault("graduation_date", "Unknown")
            resume_data.setdefault("level", "intern")
            resume_data.setdefault("is_non_traditional", False)
            resume_data.setdefault("background_context", "")
            resume_data.setdefault("education", "")
            resume_data.setdefault("experience", "")
            resume_data.setdefault("projects", "")
            resume_data.setdefault("skills", [])
            resume_data.setdefault("activities", "")
            resume_data.setdefault("raw_assessment", "")
            
            # Force intern level for non-traditional backgrounds
            if resume_data.get("is_non_traditional", False):
                resume_data["level"] = "intern"
            
            resume_data["raw_text"] = f"""
GRADUATION: {resume_data['graduation_date']}
LEVEL: {resume_data['level']}
NON-TRADITIONAL: {resume_data.get('is_non_traditional', False)}
BACKGROUND: {resume_data.get('background_context', 'N/A')}

EDUCATION:
{resume_data['education']}

EXPERIENCE:
{resume_data['experience']}

PROJECTS:
{resume_data['projects']}

SKILLS:
{', '.join(resume_data['skills'])}

ACTIVITIES:
{resume_data['activities']}

ASSESSMENT:
{resume_data['raw_assessment']}
"""
            
            return resume_data
            
        except Exception as e:
            raise Exception(f"Failed to analyze resume with Gemini: {str(e)}")
    
    def generate_initial_message(self, resume_data: Dict) -> str:
        level = resume_data["level"]
        is_non_traditional = resume_data.get("is_non_traditional", False)
        background_context = resume_data.get("background_context", "")
        
        # Special system prompt for initial greeting
        system_prompt = f"""You are an experienced technical interviewer for a {'Software Engineering Internship' if level == 'intern' else 'New Grad Software Engineering'} position.

INTERVIEW PHASE: INITIAL GREETING (NOT a behavioral question yet)
CANDIDATE LEVEL: {level.upper()}
{"NON-TRADITIONAL BACKGROUND: " + background_context if is_non_traditional else ""}

YOUR TASK:
Start with a warm, friendly greeting that makes the candidate feel comfortable.

REQUIRED GREETING STRUCTURE:
1. Introduce yourself (name + role at company)
2. Thank them for joining
3. Ask: "How's your day going so far?" or "How are you doing today?"

VARY your greeting style. Examples:
- "Hi [Name]! I'm Phoeyu, a software engineer here at Grand Piece. Thanks so much for taking the time to chat with me today. Before we dive in, how's your day going so far?"
- "Hey [Name], great to meet you! I'm [Interviewer Name] from the engineering team. Really appreciate you joining me for this interview. How are you doing today?"
- "Hello [Name]! I'm [Interviewer Name], senior engineer at [Company]. Thanks for being here today. How's your day been treating you?"

Keep it natural and conversational. DO NOT ask any behavioral questions yet - just the greeting and "how's your day" question."""
        
        user_prompt = """Generate the initial greeting for the interview. Remember: just introduce yourself, thank them, and ask how their day is going. No behavioral questions yet."""
        
        response = self._call_gemini(system_prompt, user_prompt)
        return response
    
    def process_message(
        self, 
        user_message: str, 
        resume_data: Dict, 
        questions_asked: int,
        behavioral_duration_minutes: float,
        technical_duration_minutes: float,
        current_code: str = "",
        mode: str = "behavioral",
        technical_problem_solved: bool = False,
        asked_candidate_questions: bool = False,
        transcript: list[dict] = None,
    ) -> Dict:
        if mode == "behavioral":
            # Check if should switch to technical
            should_switch = self._should_switch_to_technical(
                questions_asked, 
                behavioral_duration_minutes
            )
            
            if should_switch:
                # Generate transition response
                system_prompt = self._get_behavioral_system_prompt(resume_data, questions_asked)
                transition_prompt = f"""The candidate just said: "{user_message}"

This was their answer to behavioral question #{questions_asked}.

You need to transition to the technical coding portion now.

Respond with:
1. Brief acknowledgment of their answer (1 sentence): "Thanks for sharing that" or "That's a great example"
2. Natural transition (1 sentence): "Alright, let's move on to the technical portion now" or "Great, now I'd like to see you solve a coding problem"

Keep it SHORT (2 sentences max) and natural. DO NOT explain the problem - the system will display it.
DO NOT ask another behavioral question."""
                
                transition_message = self._call_gemini(system_prompt, transition_prompt, transcript)
                technical_data = self._generate_technical_question(resume_data["level"])
                
                return {
                    "ai_response": transition_message,
                    "should_switch_mode": True,
                    "new_mode": "technical",
                    "technical_data": technical_data,
                    "should_end_interview": False
                }
            else:
                # Continue behavioral phase
                system_prompt = self._get_behavioral_system_prompt(resume_data, questions_asked)
                
                # Improved prompt for continuing behavioral
                prompt = f"""The candidate just answered: "{user_message}"

This was their response to behavioral question #{questions_asked}.

Analyze their answer:
- If it's detailed and complete: Briefly acknowledge (1 sentence), then ask the NEXT behavioral question
- If it's vague or incomplete: Ask ONE follow-up to get more detail (STAR method: Situation, Task, Action, Result)
- If they mentioned something interesting: Probe deeper with ONE specific follow-up

CRITICAL REMINDERS:
- Do NOT ask about the same project/experience again
- Vary your question topics (if you asked teamwork, now ask problem-solving, etc.)
- Reference DIFFERENT parts of their resume
- If you asked about Project A, now ask about Project B or their internship
- Ask ONE question only
- SHOW VARIETY in your phrasing and transitions - don't sound robotic

Examples of good follow-ups if their answer was vague:
- "Can you be more specific about what YOU did in that situation?"
- "What was your exact contribution to solving that problem?"
- "How did you make that technical decision?"
- "What was the outcome - did it work?"

Examples of good transitions to next question (if their answer was complete):
- "That makes sense. Now, tell me about..." [NEW TOPIC]
- "Good example. I'm also curious about..." [DIFFERENT EXPERIENCE]
- "Great. Let me ask you about something else..." [DIFFERENT PROJECT/COMPANY]
- "Interesting. Moving on..." [NEW TOPIC]
- "I appreciate that perspective. Let's switch gears..." [DIFFERENT AREA]

Keep your response conversational and natural. Max 3-4 sentences total. VARY YOUR LANGUAGE."""
                
                ai_response = self._call_gemini(system_prompt, prompt, transcript)
                
                return {
                    "ai_response": ai_response,
                    "should_switch_mode": False,
                    "new_mode": None,
                    "technical_data": None,
                    "should_end_interview": False
                }
        
        elif mode == "technical":
            # Check if technical phase should end
            should_end_technical = self._should_end_technical_phase(
                technical_duration_minutes,
                technical_problem_solved
            )
            
            if should_end_technical and not asked_candidate_questions:
                # Transition to candidate questions
                system_prompt = self._get_technical_system_prompt(resume_data["level"])
                prompt = f"""User said: "{user_message}"

CURRENT CODE:
```python
{current_code if current_code else "# No code written yet"}
```

The technical portion is complete. Briefly acknowledge their work (1-2 sentences), then ask:
"Do you have any questions for me about the role or the company?"

Be warm and encouraging about their performance. VARY your phrasing - don't sound robotic."""
                
                ai_response = self._call_gemini(system_prompt, prompt, transcript)
                
                return {
                    "ai_response": ai_response,
                    "should_switch_mode": True,
                    "new_mode": "candidate_questions",
                    "technical_data": None,
                    "should_end_interview": False
                }
            else:
                # Continue technical guidance
                system_prompt = self._get_technical_system_prompt(resume_data["level"])
                prompt = f"""User said: "{user_message}"

CURRENT CODE IN EDITOR:
```python
{current_code if current_code else "# No code written yet"}
```

TIME SPENT: {technical_duration_minutes:.1f} minutes (max 45 minutes)

Respond naturally. Guide them through the problem:
- Ask about their approach
- Give hints if stuck (NOT solutions or algorithms)
- Help with syntax/library usage if they forget
- Provide feedback on their code
- DO NOT solve it for them

Be conversational and supportive. VARY your responses - use different phrasings and transitions."""
                
                ai_response = self._call_gemini(system_prompt, prompt, transcript)
                
                return {
                    "ai_response": ai_response,
                    "should_switch_mode": False,
                    "new_mode": None,
                    "technical_data": None,
                    "should_end_interview": False
                }
        
        elif mode == "candidate_questions":
            system_prompt = f"""You are wrapping up a {'Software Engineering Internship' if resume_data['level'] == 'intern' else 'New Grad Software Engineering'} interview.

The candidate was asked if they have questions. They said: "{user_message}"

YOUR ROLE:
- If they asked a question: Answer it professionally and concisely (2-4 sentences)
- If they said no questions or something brief: That's fine

Then say goodbye warmly and thank them for their time. VARY your goodbye phrasing - don't use the exact same wording every time. Examples:
"It was great speaking with you today. We'll be in touch soon. Best of luck!"
"Thanks for your time today. You'll hear from us shortly. Take care!"
"Really enjoyed our conversation. We'll follow up soon. Best wishes!"
"Appreciate you taking the time. We'll reach out with next steps. Good luck!"

Keep it brief and professional."""
            
            ai_response = self._call_gemini(system_prompt, user_message, transcript)
            
            return {
                "ai_response": ai_response,
                "should_switch_mode": False,
                "new_mode": None,
                "technical_data": None,
                "should_end_interview": True
            }
        
        return {
            "ai_response": "I didn't catch that, could you repeat?",
            "should_switch_mode": False,
            "new_mode": None,
            "technical_data": None,
            "should_end_interview": False
        }
    
    def process_code_execution(
        self, 
        code: str, 
        output: str, 
        status: str,
        candidate_level: str,
        technical_duration_minutes: float,
        transcript: List[Dict] = None,
    ) -> Dict:
        
        system_prompt = self._get_technical_system_prompt(candidate_level)
        prompt = f"""The candidate just ran their code (Time: {technical_duration_minutes:.1f}/45 minutes):

`CODE:
```python
{code}
```

EXECUTION STATUS: {status}
OUTPUT:
```
{output}
```

Provide feedback:
- If successful: Analyze correctness and discuss time/space complexity
- If errors: Help them debug (syntax/logic hints, NOT solutions)
- If stuck: Suggest next steps without giving algorithms

Determine if this appears to be a working solution and set problem_solved accordingly.

Be encouraging and educational. VARY your feedback style - don't use the same phrases every time."""
        
        feedback = self._call_gemini(system_prompt, prompt, transcript)
        
        # Determine if problem is solved based on status and output
        problem_solved = (
            status.lower() in ['accepted', 'success'] and 
            'error' not in output.lower() and
            output.strip() != ''
        )
        
        return {
            "feedback": feedback,
            "problem_solved": problem_solved
        }
    
    def _should_switch_to_technical(
        self, 
        questions_asked: int, 
        duration_minutes: float
    ) -> bool:
        if questions_asked >= 5:
            return True
        
        if questions_asked >= 4:
            if duration_minutes >= 8:  
                return True
            else:
                return random.random() < 0.6 
        
        if questions_asked >= 3:
            if duration_minutes >= 10:  
                return True
            elif duration_minutes >= 6:  
                return random.random() < 0.4 
            else:
               
                return random.random() < 0.1
        
       
        if questions_asked >= 2 and duration_minutes >= 15:
            return random.random() < 0.3
        
       
        return False
    
    def _should_end_technical_phase(
        self,
        technical_duration_minutes: float,
        problem_solved: bool
    ) -> bool:
        """
        Determine if technical phase should end
        """
        if problem_solved:
            return True
        
        if technical_duration_minutes >= 45:
            return True
        
        return False
    
    def _generate_technical_question(self, level: str) -> Dict:
        if level == "intern":
            problems = [
                {
                    "title": "3Sum",
                    "difficulty": "Medium",
                    "description": """Given an integer array `nums`, return all unique triplets `[nums[i], nums[j], nums[k]]` such that `i != j`, `i != k`, and `j != k`, and `nums[i] + nums[j] + nums[k] == 0`.

The solution set must not contain duplicate triplets.

**Example 1:**
Input: nums = [-1,0,1,2,-1,-4]
Output: [[-1,-1,2],[-1,0,1]]

**Example 2:**
Input: nums = [0,1,1]
Output: []

**Constraints:**
- 3 <= nums.length <= 3000
- -10^5 <= nums[i] <= 10^5""",
                    "starter_code": "def three_sum(nums):\n    # Your code here\n    pass\n\n# Test\nprint(three_sum([-1,0,1,2,-1,-4]))  # Expected: [[-1,-1,2],[-1,0,1]]",
                    "function_name": "three_sum"
                },
                {
                    "title": "Container With Most Water",
                    "difficulty": "Medium",
                    "description": """You are given an integer array `height` of length `n`. There are `n` vertical lines drawn such that the two endpoints of the `i`th line are `(i, 0)` and `(i, height[i])`.

Find two lines that together with the x-axis form a container that contains the most water.

Return the maximum amount of water a container can store.

**Example 1:**
Input: height = [1,8,6,2,5,4,8,3,7]
Output: 49
Explanation: The vertical lines are represented by array [1,8,6,2,5,4,8,3,7]. In this case, the max area of water (blue section) the container can contain is 49.

**Example 2:**
Input: height = [1,1]
Output: 1

**Constraints:**
- 2 <= n <= 10^5
- 0 <= height[i] <= 10^4""",
                    "starter_code": "def max_area(height):\n    # Your code here\n    pass\n\n# Test\nprint(max_area([1,8,6,2,5,4,8,3,7]))  # Expected: 49",
                    "function_name": "max_area"
                },
                {
                    "title": "Longest Substring Without Repeating Characters",
                    "difficulty": "Medium",
                    "description": """Given a string `s`, find the length of the longest substring without repeating characters.

**Example 1:**
Input: s = "abcabcbb"
Output: 3
Explanation: The answer is "abc", with the length of 3.

**Example 2:**
Input: s = "bbbbb"
Output: 1
Explanation: The answer is "b", with the length of 1.

**Example 3:**
Input: s = "pwwkew"
Output: 3
Explanation: The answer is "wke", with the length of 3.

**Constraints:**
- 0 <= s.length <= 5 * 10^4
- s consists of English letters, digits, symbols and spaces.""",
                    "starter_code": "def length_of_longest_substring(s):\n    # Your code here\n    pass\n\n# Test\nprint(length_of_longest_substring(\"abcabcbb\"))  # Expected: 3",
                    "function_name": "length_of_longest_substring"
                },
                {
                    "title": "Product of Array Except Self",
                    "difficulty": "Medium",
                    "description": """Given an integer array `nums`, return an array `answer` such that `answer[i]` is equal to the product of all elements of `nums` except `nums[i]`.

You must write an algorithm that runs in O(n) time and without using the division operation.

**Example 1:**
Input: nums = [1,2,3,4]
Output: [24,12,8,6]

**Example 2:**
Input: nums = [-1,1,0,-3,3]
Output: [0,0,9,0,0]

**Constraints:**
- 2 <= nums.length <= 10^5
- -30 <= nums[i] <= 30
- The product of any prefix or suffix of nums is guaranteed to fit in a 32-bit integer.

**Follow-up:**
Can you solve the problem in O(1) extra space complexity? (The output array does not count as extra space for space complexity analysis.)""",
                    "starter_code": "def product_except_self(nums):\n    # Your code here\n    pass\n\n# Test\nprint(product_except_self([1,2,3,4]))  # Expected: [24,12,8,6]",
                    "function_name": "product_except_self"
                },
                {
                    "title": "Valid Parentheses",
                    "difficulty": "Easy",
                    "description": """Given a string `s` containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.

An input string is valid if:
1. Open brackets must be closed by the same type of brackets.
2. Open brackets must be closed in the correct order.
3. Every close bracket has a corresponding open bracket of the same type.

**Example 1:**
Input: s = "()"
Output: true

**Example 2:**
Input: s = "()[]{}"
Output: true

**Example 3:**
Input: s = "(]"
Output: false

**Constraints:**
- 1 <= s.length <= 10^4
- s consists of parentheses only '()[]{}'""",
                    "starter_code": "def is_valid(s):\n    # Your code here\n    pass\n\n# Test\nprint(is_valid(\"()\"))  # Expected: True\nprint(is_valid(\"()[]{}\"))  # Expected: True\nprint(is_valid(\"(]\"))  # Expected: False",
                    "function_name": "is_valid"
                }
            ]
        else:  # new_grad
            problems = [
                {
                    "title": "Trapping Rain Water",
                    "difficulty": "Hard",
                    "description": """Given `n` non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining.

**Example 1:**
Input: height = [0,1,0,2,1,0,1,3,2,1,2,1]
Output: 6
Explanation: The elevation map is represented by array [0,1,0,2,1,0,1,3,2,1,2,1]. In this case, 6 units of rain water (blue section) are being trapped.

**Example 2:**
Input: height = [4,2,0,3,2,5]
Output: 9

**Constraints:**
- 1 <= n <= 2 * 10^4
- 0 <= height[i] <= 10^5""",
                    "starter_code": "def trap(height):\n    # Your code here\n    pass\n\n# Test\nprint(trap([0,1,0,2,1,0,1,3,2,1,2,1]))  # Expected: 6",
                    "function_name": "trap"
                },
                {
                    "title": "Merge K Sorted Lists",
                    "difficulty": "Hard",
                    "description": """You are given an array of `k` linked-lists `lists`, each linked-list is sorted in ascending order.

Merge all the linked-lists into one sorted linked-list and return it.

**Example 1:**
Input: lists = [[1,4,5],[1,3,4],[2,6]]
Output: [1,1,2,3,4,4,5,6]
Explanation: The linked-lists are:
[
  1->4->5,
  1->3->4,
  2->6
]
merging them into one sorted list:
1->1->2->3->4->4->5->6

**Example 2:**
Input: lists = []
Output: []

**Example 3:**
Input: lists = [[]]
Output: []

**Constraints:**
- k == lists.length
- 0 <= k <= 10^4
- 0 <= lists[i].length <= 500
- -10^4 <= lists[i][j] <= 10^4
- lists[i] is sorted in ascending order.

**Note:** For simplicity, work with lists instead of linked lists""",
                    "starter_code": "def merge_k_lists(lists):\n    # Your code here\n    pass\n\n# Test\nprint(merge_k_lists([[1,4,5],[1,3,4],[2,6]]))  # Expected: [1,1,2,3,4,4,5,6]",
                    "function_name": "merge_k_lists"
                },
                {
                    "title": "Minimum Window Substring",
                    "difficulty": "Hard",
                    "description": """Given two strings `s` and `t` of lengths `m` and `n` respectively, return the minimum window substring of `s` such that every character in `t` (including duplicates) is included in the window. If there is no such substring, return the empty string "".

**Example 1:**
Input: s = "ADOBECODEBANC", t = "ABC"
Output: "BANC"
Explanation: The minimum window substring "BANC" includes 'A', 'B', and 'C' from string t.

**Example 2:**
Input: s = "a", t = "a"
Output: "a"
Explanation: The entire string s is the minimum window.

**Example 3:**
Input: s = "a", t = "aa"
Output: ""
Explanation: Both 'a's from t must be included in the window. Since the largest window of s only has one 'a', return empty string.

**Constraints:**
- 1 <= s.length, t.length <= 10^5
- s and t consist of uppercase and lowercase English letters.

**Follow-up:**
Could you find an algorithm that runs in O(m + n) time?""",
                    "starter_code": "def min_window(s, t):\n    # Your code here\n    pass\n\n# Test\nprint(min_window(\"ADOBECODEBANC\", \"ABC\"))  # Expected: \"BANC\"",
                    "function_name": "min_window"
                },
                {
                    "title": "Word Ladder",
                    "difficulty": "Hard",
                    "description": """A transformation sequence from word `beginWord` to word `endWord` using a dictionary `wordList` is a sequence of words beginWord -> s1 -> s2 -> ... -> sk such that:

- Every adjacent pair of words differs by a single letter.
- Every si for 1 <= i <= k is in wordList. Note that beginWord does not need to be in wordList.
- sk == endWord

Given two words, beginWord and endWord, and a dictionary wordList, return the number of words in the shortest transformation sequence from beginWord to endWord, or 0 if no such sequence exists.

**Example 1:**
Input: beginWord = "hit", endWord = "cog", wordList = ["hot","dot","dog","lot","log","cog"]
Output: 5
Explanation: One shortest transformation sequence is "hit" -> "hot" -> "dot" -> "dog" -> "cog", which is 5 words long.

**Example 2:**
Input: beginWord = "hit", endWord = "cog", wordList = ["hot","dot","dog","lot","log"]
Output: 0
Explanation: The endWord "cog" is not in wordList, therefore there is no valid transformation sequence.

**Constraints:**
- 1 <= beginWord.length <= 10
- endWord.length == beginWord.length
- 1 <= wordList.length <= 5000
- wordList[i].length == beginWord.length
- beginWord, endWord, and wordList[i] consist of lowercase English letters.
- beginWord != endWord
- All the words in wordList are unique.""",
                    "starter_code": "def ladder_length(beginWord, endWord, wordList):\n    # Your code here\n    pass\n\n# Test\nprint(ladder_length(\"hit\", \"cog\", [\"hot\",\"dot\",\"dog\",\"lot\",\"log\",\"cog\"]))  # Expected: 5",
                    "function_name": "ladder_length"
                }
            ]
        
        # Return a random problem from the list
        return random.choice(problems)
    
    def generate_evaluation(
        self, 
        transcript: List[Dict], 
        final_code: str,
        candidate_level: str,
        technical_question_title: str,
        technical_duration_minutes: float
    ) -> Dict:
        """
        Generate final interview evaluation
        """
        transcript_text = "\n".join([
            f"{msg['speaker']}: {msg['message']}"
            for msg in transcript
        ])
        
        evaluation_prompt = f"""You are evaluating a {'Software Engineering Intern' if candidate_level == 'intern' else 'New Grad Software Engineering'} interview.

CANDIDATE LEVEL: {candidate_level.upper()}
TECHNICAL PROBLEM: {technical_question_title}
TIME SPENT: {technical_duration_minutes:.1f} minutes

TRANSCRIPT:
{transcript_text}

FINAL CODE:
```python
{final_code if final_code else "No code submitted"}
```

Provide evaluation in JSON:
{{
  "behavioral_score": <0-10>,
  "technical_score": <0-10>,
  "overall_score": <0-10>,
  "strengths": [<3-4 items>],
  "improvements": [<3-4 items>],
  "detailed_feedback": "<2-3 paragraphs>",
  "recommendation": "<Strong Hire | Hire | No Hire | Strong No Hire>"
}}

Be fair. Most candidates score 5-7."""
        
        system_prompt = "You are an expert technical interviewer. Respond ONLY with valid JSON."
        
        response = self._call_gemini(system_prompt, evaluation_prompt, transcript)
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                evaluation = json.loads(json_match.group())
            else:
                evaluation = json.loads(response)
            
            return evaluation
        except json.JSONDecodeError:
            return {
                "behavioral_score": 5,
                "technical_score": 5,
                "overall_score": 5,
                "strengths": ["Completed interview"],
                "improvements": ["Continue practicing"],
                "detailed_feedback": "Evaluation unavailable",
                "recommendation": "No Hire"
            }
    
    def _get_behavioral_system_prompt(self, resume_data: Dict, questions_asked: int) -> str:
        """
        Generate system prompt for behavioral phase with better variety and non-traditional adaptiveness
        """
        level = resume_data["level"]
        is_non_traditional = resume_data.get("is_non_traditional", False)
        background_context = resume_data.get("background_context", "")
        
        # Add non-traditional context if applicable
        non_traditional_note = ""
        if is_non_traditional:
            non_traditional_note = f"""
⚠️ NON-TRADITIONAL CANDIDATE DETECTED ⚠️
Background: {background_context}
- This candidate does NOT have a traditional CS background
- They are being placed at INTERN level regardless of graduation date
- BE REALISTIC and acknowledge this in your questioning
- Still conduct a professional SWE interview, but adapt your approach

SPECIAL INSTRUCTIONS FOR NON-TRADITIONAL CANDIDATES:
- If this is question #1 or #2, you MUST acknowledge their unique background
- Examples of natural acknowledgment:
  * "I notice your background is in {background_context} - that's quite different from most candidates. What made you interested in switching to software engineering?"
  * "Your resume shows a lot of experience in {background_context}. I'm curious what drew you to pursue software engineering?"
  * "This is interesting - you come from a {background_context} background. Walk me through your journey into tech."
- After acknowledging, still ask behavioral questions but ADAPT them:
  * Focus on transferable skills (teamwork, problem-solving, learning)
  * Ask about technical projects they HAVE done (bootcamp, personal projects, online courses)
  * Don't expect traditional SWE internship stories
  * Be encouraging about their career transition
"""
        
        # Determine question focus
        question_focus = ""
        if questions_asked == 1:
            if is_non_traditional:
                question_focus = """FIRST QUESTION - MUST acknowledge non-traditional background:
Examples:
- "I see you're coming from a {background} background - that's quite a transition! What sparked your interest in software engineering?"
- "Your resume shows {background} experience rather than traditional CS. I'm curious what made you want to pivot to tech?"
- "Interesting background you have here. Walk me through how you went from {background} to pursuing software engineering."

Be warm, genuinely curious, and encouraging. This is their chance to tell their story."""
            else:
                question_focus = """FIRST QUESTION - Warm opener:
VARY your phrasing. Examples:
- "Tell me about yourself and what interests you in software engineering"
- "Walk me through your background - how did you get into programming?"
- "I'd love to hear about your journey into software engineering"
- "Start by telling me a bit about yourself and your experience with coding"

Keep it open-ended and natural."""
        
        elif questions_asked == 2:
            if is_non_traditional:
                question_focus = """SECOND QUESTION - Ask about their technical journey:
Focus on HOW they learned to code and what they've built:
- "Tell me about your first technical project - what was it and how did you approach it?"
- "Walk me through one of your projects. What did you build and why?"
- "What's been the most challenging technical problem you've tackled so far?"
- "Describe a project where you learned something completely new"

Be realistic - they likely don't have SWE internships. Focus on bootcamp projects, self-taught work, or coursework."""
            else:
                question_focus = """SECOND QUESTION - PRIORITIZE WORK EXPERIENCE:
If they have SWE internships/jobs, ask about those FIRST:
- "Tell me about your experience at [Company]. What was your biggest contribution?"
- "Walk me through a challenge you faced at [Company]"
- "What was the most impactful project you worked on at [Company]?"

If NO work experience, ask about their best project.
VARY your phrasing."""
        
        elif questions_asked == 3:
            if is_non_traditional:
                question_focus = """THIRD QUESTION - Transferable skills (teamwork/collaboration):
Frame around ANY team experience (doesn't have to be SWE):
- "Tell me about a time you worked with a team on a project - technical or not"
- "Describe a situation where you had to collaborate with others who had different skills"
- "Give me an example of working through a disagreement with a teammate"
- "Tell me about your experience working in team settings"

Accept non-SWE examples but encourage them to tie it to technical work if possible."""
            else:
                question_focus = """THIRD QUESTION - Teamwork/collaboration:
- "Tell me about a time you disagreed with a teammate"
- "Describe working with a difficult team member"
- "Give an example of compromising on a technical decision"
- "Walk me through a challenging group project"

VARY your phrasing and transitions."""
        
        elif questions_asked == 4:
            question_focus = """FOURTH QUESTION - Problem-solving:
Examples (VARY your phrasing):
- "Tell me about a technical challenge you didn't know how to solve initially"
- "Describe debugging a difficult issue"
- "Example of learning something new under pressure"
- "Walk me through a time you were stuck on a problem - how did you get unstuck?"
- "Tell me about the hardest bug you've encountered"

For non-traditional: Accept any technical problem-solving, even if from learning/bootcamp context."""
        
        elif questions_asked >= 5:
            question_focus = """FIFTH+ QUESTION - Leadership/impact/growth:
Examples (VARY your phrasing):
- "Tell me about a time you took initiative on a project"
- "What's the most important technical decision you've made?"
- "Describe your biggest achievement in software engineering"
- "Tell me about something you built that you're really proud of"
- "Walk me through a time you had to teach yourself something completely new"

Vary topics - don't repeat previous themes. Be creative with your questions."""
        
        prompt = f"""You are an experienced technical interviewer for a Software Engineering Internship position.

INTERVIEW PHASE: BEHAVIORAL (Question {questions_asked}/5)
CANDIDATE LEVEL: {level.upper()}

{non_traditional_note}

CRITICAL RULES:
1. Resume PDF is attached - see ALL experience and projects
2. PRIORITIZE SWE work experience over projects (unless non-traditional)
3. NEVER ask about same project/experience twice
4. Vary question topics across different questions
5. Reference SPECIFIC details from resume
6. Ask ONE question at a time
7. SHOW DIVERSITY in your language - don't sound repetitive or robotic
8. Use different transition phrases and acknowledgments

{question_focus}

CONVERSATION STYLE:
- Warm, professional, encouraging
- Show genuine interest and curiosity
- VARY your transitions and acknowledgments:
  * "That makes sense", "Interesting", "I see", "Good example", "Great", "I appreciate that", "Understood", "Got it", "Makes sense"
- Probe if vague: "Can you be more specific?", "Tell me more about that", "What exactly did you do?", "Walk me through that"
- DON'T use the same phrases repeatedly

DO NOT:
- Mention switching phases or interview structure
- Ask yes/no questions
- Ask multiple questions at once
- Repeat same project/experience
- Sound robotic or formulaic

DIVERSITY IN RESPONSES:
- Vary greeting style each time
- Use different acknowledgment phrases
- Change up transition language
- Don't follow the exact same pattern every question
- Be naturally conversational, not scripted

Check resume PDF for multiple internships/projects. Reference different ones."""
        
        return prompt
    
    def _get_technical_system_prompt(self, level: str) -> str:
        """
        Generate system prompt for technical phase
        """
        prompt = f"""You are an experienced technical interviewer for a Software Engineering Internship position.

INTERVIEW PHASE: TECHNICAL (MAX 45 MIN)
CANDIDATE LEVEL: {level.upper()}

YOUR ROLE:
- Guide through problem
- See code in real-time
- Ask about approach first
- Provide hints (NOT solutions)
- Help with syntax if forgotten
- Analyze results when they run code
- Discuss time/space complexity

GUIDANCE: {'Be more helpful, clearer hints' if level == 'intern' else 'Expect them to drive more'}

Be conversational, not robotic. VARY your language and responses:
- Different ways to ask about approach: "What's your plan?", "How would you tackle this?", "Walk me through your thinking", "What approach are you considering?"
- Different hints: "Think about...", "Consider...", "What if you...", "Have you thought about...", "Another approach might be..."
- Different encouragements: "Good thinking", "You're on the right track", "That makes sense", "Exactly", "Nice", "Good idea"

Don't use the same phrases every time."""
        
        return prompt
    
    def _call_gemini(self, system_prompt: str, user_prompt: str, transcript: List[Dict] = None) -> str:
        try:
            # build convo history from transcript
            history_text = ""
            if transcript and len(transcript) > 0:
                history_text = "\n\nCONVERSATION HISTORY:\n"
                for msg in transcript:
                    history_text += f"{msg['speaker']}: {msg['message']}\n"
                history_text += "\n"
            
            full_prompt = f"{system_prompt}\n\n{history_text}{user_prompt}"
            
            
            if self.uploaded_resume_file:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[self.uploaded_resume_file, full_prompt]
                )
            else:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[full_prompt]
                )
            
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API error: {e}")
            return "Sorry I didn't get that I think I'm dying."
