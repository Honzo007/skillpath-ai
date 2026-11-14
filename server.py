"""Standalone Web Server for SkillForge AI on port 8501.
Runs with Python standard library, providing instant zero-delay localhost access to the multi-agent platform.
"""
import os
import json
import http.server
import socketserver
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Import multi-agent orchestrator
import sys
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from agents.orchestrator import Orchestrator

DATA_DIR = BASE_DIR / "data"
ROLES_FILE = DATA_DIR / "roles.json"
QUIZZES_FILE = DATA_DIR / "quizzes.json"
LEARNER_FILE = DATA_DIR / "learner.json"

orchestrator = Orchestrator()

def load_json(p: Path):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_learner(data):
    try:
        with open(LEARNER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

roles_data = load_json(ROLES_FILE)
quizzes_data = load_json(QUIZZES_FILE)
learner_state = load_json(LEARNER_FILE)

# Initial analysis run
initial_res = orchestrator.handle_event("new_profile", learner_state, roles_data, quizzes_data)
learner_state["last_analysis"] = initial_res

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SkillForge AI | Adaptive Learning Platform</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f8fafc; }
    .badge-matched { background-color: #dcfce7; color: #166534; }
    .badge-missing { background-color: #fee2e2; color: #991b1b; }
    .log-box { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
  </style>
</head>
<body class="flex min-h-screen">

  <!-- SIDEBAR -->
  <aside class="w-80 bg-slate-900 text-slate-100 p-6 flex flex-col justify-between shrink-0 shadow-xl">
    <div>
      <div class="flex items-center space-x-3 mb-6">
        <span class="text-3xl">🎯</span>
        <div>
          <h1 class="text-xl font-bold tracking-tight text-white">SkillForge AI</h1>
          <p class="text-xs text-cyan-400">Multi-Agent Adaptive Platform</p>
        </div>
      </div>

      <!-- Mode Badge -->
      <div class="mb-5 bg-slate-800 rounded-lg p-3 border border-slate-700">
        <div class="flex items-center space-x-2 text-xs">
          <span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span class="font-medium text-slate-300">System Ready & Active</span>
        </div>
        <div class="text-[11px] text-slate-400 mt-1">Localhost Host Port: 8501</div>
      </div>

      <!-- Demo Controls -->
      <div class="mb-6">
        <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">PromptWars Demo</h3>
        <button onclick="loadDemo()" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 px-4 rounded-lg text-sm shadow transition flex items-center justify-center space-x-2">
          <span>📥</span>
          <span>Load Demo Scenario</span>
        </button>
        <p class="text-[11px] text-slate-400 mt-1 text-center">Alex Chen → Full Stack Developer</p>
      </div>

      <!-- Goal Switch -->
      <div class="mb-6">
        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Quick Switch Role</label>
        <select id="role-select" onchange="switchRole(this.value)" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500">
          <option value="Full Stack Developer">Full Stack Developer</option>
          <option value="Data Scientist">Data Scientist</option>
          <option value="DevOps Engineer">DevOps Engineer</option>
        </select>
      </div>

      <!-- Live Agent Activity -->
      <div class="mt-4">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1">
            <span>🤖</span>
            <span>Live Agent Activity</span>
          </h3>
          <span class="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-cyan-400 font-mono" id="log-count">0 events</span>
        </div>
        <div id="activity-log" class="log-box bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-cyan-300 h-64 overflow-y-auto space-y-1.5 text-[11px]">
          <!-- Logs go here -->
        </div>
      </div>
    </div>

    <div class="pt-4 border-t border-slate-800 text-[11px] text-slate-500 text-center">
      SkillForge AI Prototype • PromptWars 2026
    </div>
  </aside>

  <!-- MAIN CONTENT -->
  <main class="flex-1 p-8 overflow-y-auto max-w-6xl">
    
    <!-- NAVIGATION TABS -->
    <div class="flex border-b border-slate-200 mb-6 space-x-2">
      <button onclick="setTab('analysis')" id="tab-btn-analysis" class="py-3 px-5 font-medium text-sm border-b-2 border-blue-600 text-blue-600 transition flex items-center space-x-2">
        <span>📊</span>
        <span>Skill Gap Analysis</span>
      </button>
      <button onclick="setTab('profile')" id="tab-btn-profile" class="py-3 px-5 font-medium text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-800 transition flex items-center space-x-2">
        <span>👤</span>
        <span>Learner Profile</span>
      </button>
      <button onclick="setTab('roadmap')" id="tab-btn-roadmap" class="py-3 px-5 font-medium text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-800 transition flex items-center space-x-2">
        <span>🗺️</span>
        <span>Curriculum Roadmap</span>
      </button>
      <button onclick="setTab('quiz')" id="tab-btn-quiz" class="py-3 px-5 font-medium text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-800 transition flex items-center space-x-2">
        <span>📝</span>
        <span>Skill Assessment</span>
      </button>
      <button onclick="setTab('mentor')" id="tab-btn-mentor" class="py-3 px-5 font-medium text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-800 transition flex items-center space-x-2">
        <span>💬</span>
        <span>AI Mentor Guidance</span>
      </button>
    </div>

    <!-- TAB 1: SKILL GAP ANALYSIS -->
    <section id="tab-analysis" class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-bold text-slate-800">Skill Gap Analysis & Career Match</h2>
          <p class="text-sm text-slate-500">Deterministic requirements evaluation for <span id="header-target-role" class="font-semibold text-blue-600">Full Stack Developer</span></p>
        </div>
      </div>

      <!-- METRIC CARDS -->
      <div class="grid grid-cols-4 gap-4">
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div class="text-xs uppercase font-medium text-slate-400">Target Role</div>
          <div id="stat-role" class="text-lg font-bold text-slate-800 mt-1">Full Stack Developer</div>
        </div>
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div class="text-xs uppercase font-medium text-slate-400">Readiness Score</div>
          <div id="stat-readiness" class="text-2xl font-black text-blue-600 mt-1">50.0%</div>
        </div>
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div class="text-xs uppercase font-medium text-slate-400">Verified Strengths</div>
          <div id="stat-matched" class="text-2xl font-bold text-emerald-600 mt-1">3 / 6</div>
        </div>
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div class="text-xs uppercase font-medium text-slate-400">Detected Skill Gaps</div>
          <div id="stat-missing" class="text-2xl font-bold text-rose-600 mt-1">3</div>
        </div>
      </div>

      <!-- READINESS PROGRESS BAR -->
      <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div class="flex justify-between text-sm font-semibold mb-2">
          <span class="text-slate-700">Role Readiness Progression</span>
          <span id="progress-pct" class="text-blue-600">50% Complete</span>
        </div>
        <div class="w-full bg-slate-100 rounded-full h-4 overflow-hidden">
          <div id="progress-bar-fill" class="bg-blue-600 h-4 rounded-full transition-all duration-500" style="width: 50%;"></div>
        </div>
      </div>

      <!-- TWO COLUMNS: SKILLS & COVERAGE CHART -->
      <div class="grid grid-cols-2 gap-6">
        <!-- Matched & Missing Lists -->
        <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5">
          <h3 class="text-base font-bold text-slate-800">🔍 Verified Skills vs Missing Gaps</h3>
          <div>
            <div class="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-2">✅ Matched & Verified Competencies</div>
            <div id="matched-tags" class="flex flex-wrap gap-2"></div>
          </div>
          <div class="pt-3 border-t border-slate-100">
            <div class="text-xs font-semibold text-rose-700 uppercase tracking-wide mb-2">⚠️ Missing Skills Required for Target Role</div>
            <div id="missing-tags" class="flex flex-wrap gap-2"></div>
          </div>
        </div>

        <!-- Coverage Overview -->
        <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <h3 class="text-base font-bold text-slate-800 mb-2">📈 Skill Coverage Distribution</h3>
          <div class="space-y-4 my-auto">
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <span class="text-emerald-700">Acquired Skills</span>
                <span id="chart-matched-val" class="font-bold">3 skills</span>
              </div>
              <div class="w-full bg-slate-100 rounded-full h-3">
                <div id="chart-matched-bar" class="bg-emerald-500 h-3 rounded-full" style="width: 50%"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <span class="text-rose-700">Missing Gaps to Bridge</span>
                <span id="chart-missing-val" class="font-bold">3 skills</span>
              </div>
              <div class="w-full bg-slate-100 rounded-full h-3">
                <div id="chart-missing-bar" class="bg-rose-500 h-3 rounded-full" style="width: 50%"></div>
              </div>
            </div>
          </div>
          <div class="bg-slate-50 p-3 rounded-lg border border-slate-100 text-xs text-slate-500 text-center">
            Prerequisites are topologically sorted in the <strong>Curriculum Roadmap</strong> tab.
          </div>
        </div>
      </div>

      <!-- SkillAnalyst Summary -->
      <div class="bg-blue-50 border-l-4 border-blue-600 p-5 rounded-r-xl shadow-sm">
        <h4 class="text-sm font-bold text-blue-900 mb-1 flex items-center space-x-2">
          <span>🧠</span>
          <span>SkillAnalyst AI Assessment</span>
        </h4>
        <p id="analyst-summary" class="text-sm text-blue-800 leading-relaxed"></p>
      </div>
    </section>

    <!-- TAB 2: PROFILE -->
    <section id="tab-profile" class="hidden space-y-6">
      <div>
        <h2 class="text-2xl font-bold text-slate-800">Learner Profile</h2>
        <p class="text-sm text-slate-500">Configure your skill portfolio, projects, and career goal.</p>
      </div>

      <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Full Name</label>
            <input type="text" id="prof-name" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Target Career Role</label>
            <select id="prof-target" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500">
              <option value="Full Stack Developer">Full Stack Developer</option>
              <option value="Data Scientist">Data Scientist</option>
              <option value="DevOps Engineer">DevOps Engineer</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Current Skills (comma-separated)</label>
          <input type="text" id="prof-skills" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" placeholder="Python, SQL, HTML & CSS">
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Certifications (one per line)</label>
            <textarea id="prof-certs" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"></textarea>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Projects (one per line)</label>
            <textarea id="prof-projects" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"></textarea>
          </div>
        </div>

        <button onclick="saveProfile()" class="bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-6 rounded-lg text-sm shadow">
          💾 Save Profile & Re-analyze Gaps
        </button>
      </div>
    </section>

    <!-- TAB 3: ROADMAP -->
    <section id="tab-roadmap" class="hidden space-y-6">
      <div>
        <h2 class="text-2xl font-bold text-slate-800">Personalized Learning Roadmap</h2>
        <p class="text-sm text-slate-500">Prerequisite-ordered curriculum using curated, verified educational resources.</p>
      </div>
      <div id="roadmap-container" class="space-y-4"></div>
    </section>

    <!-- TAB 4: QUIZ -->
    <section id="tab-quiz" class="hidden space-y-6">
      <div>
        <h2 class="text-2xl font-bold text-slate-800">Skill Diagnostic Assessment</h2>
        <p class="text-sm text-slate-500">Complete assessments to unlock next milestones or generate adaptive revision steps.</p>
      </div>
      <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div class="flex items-center space-x-4">
          <label class="text-sm font-semibold text-slate-700">Choose Skill to Test:</label>
          <select id="quiz-skill-select" onchange="renderQuiz(this.value)" class="border border-slate-300 rounded-lg px-3 py-1.5 text-sm"></select>
        </div>
        <div id="quiz-questions-area" class="space-y-6 pt-4 border-t border-slate-100"></div>
      </div>
    </section>

    <!-- TAB 5: MENTOR -->
    <section id="tab-mentor" class="hidden space-y-6">
      <div>
        <h2 class="text-2xl font-bold text-slate-800">AI Mentor Guidance</h2>
        <p class="text-sm text-slate-500">Dynamic personalized feedback explaining plan adaptations.</p>
      </div>
      <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-start space-x-4">
        <span class="text-4xl">🤖</span>
        <div class="space-y-2">
          <div class="text-xs font-bold text-blue-600 uppercase">AI Learning Coach</div>
          <div id="mentor-message-text" class="text-base text-slate-800 leading-relaxed font-normal bg-slate-50 p-4 rounded-xl border border-slate-200"></div>
        </div>
      </div>
    </section>

  </main>

  <script>
    let appState = null;

    async function fetchState() {
      const res = await fetch('/api/state');
      appState = await res.json();
      renderAll();
    }

    function renderAll() {
      if (!appState) return;
      const profile = appState.profile || {};
      const analysis = appState.last_analysis || {};
      const cm = analysis.career_match || {};
      const sa = analysis.skill_analysis || {};
      const cp = analysis.curriculum || {};
      const mentor = analysis.mentor || {};
      const logs = appState.activity_log || [];

      // Sidebar
      document.getElementById('role-select').value = profile.target_role || "Full Stack Developer";
      document.getElementById('log-count').innerText = `${logs.length} events`;
      const logBox = document.getElementById('activity-log');
      logBox.innerHTML = logs.map(l => `<div class="py-0.5">• ${l}</div>`).join('');

      // Header & Stats
      document.getElementById('header-target-role').innerText = profile.target_role || "Role";
      document.getElementById('stat-role').innerText = profile.target_role || "Role";
      document.getElementById('stat-readiness').innerText = `${cm.readiness_score || 0}%`;
      document.getElementById('stat-matched').innerText = `${(cm.matched_skills || []).length} / ${(cm.total_skills || []).length}`;
      document.getElementById('stat-missing').innerText = `${(cm.missing_skills || []).length}`;

      // Progress bar
      const pct = cm.readiness_score || 0;
      document.getElementById('progress-pct').innerText = `${pct}% Complete`;
      document.getElementById('progress-bar-fill').style.width = `${pct}%`;

      // Tags
      const matchedEl = document.getElementById('matched-tags');
      matchedEl.innerHTML = (cm.matched_skills || []).length
        ? (cm.matched_skills || []).map(s => `<span class="badge-matched font-medium text-xs px-3 py-1 rounded-full">✓ ${s}</span>`).join('')
        : `<span class="text-xs text-slate-400">No verified skills yet</span>`;

      const missingEl = document.getElementById('missing-tags');
      missingEl.innerHTML = (cm.missing_skills || []).length
        ? (cm.missing_skills || []).map(s => `<span class="badge-missing font-medium text-xs px-3 py-1 rounded-full">✕ ${s}</span>`).join('')
        : `<span class="text-xs text-emerald-600 font-semibold">🎉 All core skills acquired!</span>`;

      // Coverage Chart
      const mCount = (cm.matched_skills || []).length;
      const gCount = (cm.missing_skills || []).length;
      const total = mCount + gCount || 1;
      document.getElementById('chart-matched-val').innerText = `${mCount} skills (${Math.round(mCount/total*100)}%)`;
      document.getElementById('chart-missing-val').innerText = `${gCount} skills (${Math.round(gCount/total*100)}%)`;
      document.getElementById('chart-matched-bar').style.width = `${(mCount/total*100)}%`;
      document.getElementById('chart-missing-bar').style.width = `${(gCount/total*100)}%`;

      // Analyst
      document.getElementById('analyst-summary').innerText = sa.summary || "Evaluating profile...";

      // Profile Form
      document.getElementById('prof-name').value = profile.name || "";
      document.getElementById('prof-target').value = profile.target_role || "Full Stack Developer";
      document.getElementById('prof-skills').value = (profile.skills || []).join(', ');
      document.getElementById('prof-certs').value = (profile.certifications || []).join('\\n');
      document.getElementById('prof-projects').value = (profile.projects || []).join('\\n');

      // Roadmap
      const roadmapContainer = document.getElementById('roadmap-container');
      const steps = cp.roadmap || [];
      if (!steps.length) {
        roadmapContainer.innerHTML = `<div class="bg-white p-6 rounded-xl border border-slate-200 text-slate-500">No missing gaps! Your profile is ready for this role.</div>`;
      } else {
        roadmapContainer.innerHTML = steps.map(st => `
          <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-3">
                <span class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${st.status === 'done' ? 'bg-emerald-100 text-emerald-700' : (st.status === 'in_progress' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500')}">
                  ${st.status === 'done' ? '✓' : st.step_number}
                </span>
                <div>
                  <h4 class="font-bold text-slate-800 text-base">${st.skill}</h4>
                  <div class="text-xs text-slate-400">Difficulty: ${st.difficulty} • Prerequisites: ${(st.prerequisites || []).join(', ') || 'None'}</div>
                </div>
              </div>
              <span class="text-xs font-semibold px-2.5 py-1 rounded uppercase tracking-wider ${st.status === 'done' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : (st.status === 'in_progress' ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-slate-100 text-slate-500')}">
                ${st.status}
              </span>
            </div>
            <div class="pt-2 border-t border-slate-100 space-y-2">
              <div class="text-xs font-bold text-slate-600 uppercase">Curated Learning Resources:</div>
              <div class="grid grid-cols-3 gap-3">
                ${(st.resources || []).map(r => `
                  <a href="${r.url}" target="_blank" class="block p-3 rounded-lg border border-slate-200 hover:border-blue-400 bg-slate-50 transition text-xs">
                    <div class="font-semibold text-blue-600 truncate">${r.title}</div>
                    <div class="text-[11px] text-slate-400 mt-1 uppercase">${r.type} • ~${r.estimated_hours}h</div>
                  </a>
                `).join('')}
              </div>
            </div>
          </div>
        `).join('');
      }

      // Quiz Selector
      const quizSelect = document.getElementById('quiz-skill-select');
      const missingSkills = cm.missing_skills || [];
      const skillsToTest = missingSkills.length ? missingSkills : Object.keys(appState.quizzes || {});
      quizSelect.innerHTML = skillsToTest.map(s => `<option value="${s}">${s}</option>`).join('');
      if (skillsToTest.length) {
        renderQuiz(skillsToTest[0]);
      }

      // Mentor
      document.getElementById('mentor-message-text').innerText = mentor.message || "Welcome! Follow your personalized steps to master your career goal.";
    }

    function renderQuiz(skill) {
      const qList = (appState.quizzes && appState.quizzes[skill]) || [];
      const area = document.getElementById('quiz-questions-area');
      if (!qList.length) {
        area.innerHTML = `<div class="text-slate-500 text-sm">No quiz questions currently available for ${skill}.</div>`;
        return;
      }
      area.innerHTML = `
        <div class="text-sm font-bold text-slate-700 mb-2">Diagnostic Quiz for: <span class="text-blue-600">${skill}</span> (${qList.length} Questions)</div>
        <form id="quiz-form" onsubmit="submitQuiz(event, '${skill}')" class="space-y-5">
          ${qList.map((q, idx) => `
            <div class="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <div class="text-sm font-semibold text-slate-800 mb-3">${idx+1}. ${q.question}</div>
              <div class="space-y-2">
                ${(q.options || []).map(opt => `
                  <label class="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer p-1.5 rounded hover:bg-slate-100">
                    <input type="radio" name="${q.id}" value="${opt.replace(/"/g, '&quot;')}" required class="text-blue-600">
                    <span>${opt}</span>
                  </label>
                `).join('')}
              </div>
            </div>
          `).join('')}
          <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2 px-6 rounded-lg text-sm shadow">
            Submit Assessment
          </button>
        </form>
        <div id="quiz-result-feedback" class="hidden mt-4 p-4 rounded-xl text-sm"></div>
      `;
    }

    async function submitQuiz(e, skill) {
      e.preventDefault();
      const form = document.getElementById('quiz-form');
      const formData = new FormData(form);
      const answers = {};
      for (const [key, val] of formData.entries()) {
        answers[key] = val;
      }
      const res = await fetch('/api/quiz', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ skill: skill, answers: answers })
      });
      const data = await res.json();
      const fb = document.getElementById('quiz-result-feedback');
      fb.classList.remove('hidden');
      if (data.score >= 80) {
        fb.className = "mt-4 p-4 rounded-xl text-sm bg-emerald-50 border border-emerald-200 text-emerald-800";
        fb.innerHTML = `<strong>🎉 Mastered! Score: ${data.score}%</strong>. ${data.skill} is marked complete and subsequent steps unlocked!`;
      } else if (data.score < 60) {
        fb.className = "mt-4 p-4 rounded-xl text-sm bg-amber-50 border border-amber-200 text-amber-800";
        fb.innerHTML = `<strong>⚠️ Score: ${data.score}%</strong>. Score is below 60%. Revision steps have been injected into your roadmap.`;
      } else {
        fb.className = "mt-4 p-4 rounded-xl text-sm bg-blue-50 border border-blue-200 text-blue-800";
        fb.innerHTML = `<strong>Score: ${data.score}%</strong>. Solid effort! Review the explanations and proceed.`;
      }
      setTimeout(fetchState, 1200);
    }

    async function loadDemo() {
      const res = await fetch('/api/demo', { method: 'POST' });
      await fetchState();
    }

    async function switchRole(role) {
      const res = await fetch('/api/switch_role', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ role: role })
      });
      await fetchState();
    }

    async function saveProfile() {
      const skillsStr = document.getElementById('prof-skills').value;
      const skills = skillsStr.split(',').map(s => s.trim()).filter(Boolean);
      const payload = {
        name: document.getElementById('prof-name').value,
        target_role: document.getElementById('prof-target').value,
        skills: skills,
        certifications: document.getElementById('prof-certs').value.split('\\n').filter(Boolean),
        projects: document.getElementById('prof-projects').value.split('\\n').filter(Boolean)
      };
      await fetch('/api/save_profile', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      await fetchState();
      setTab('analysis');
    }

    function setTab(tabName) {
      ['analysis', 'profile', 'roadmap', 'quiz', 'mentor'].forEach(t => {
        document.getElementById(`tab-${t}`).classList.add('hidden');
        document.getElementById(`tab-btn-${t}`).className = "py-3 px-5 font-medium text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-800 transition flex items-center space-x-2";
      });
      document.getElementById(`tab-${tabName}`).classList.remove('hidden');
      document.getElementById(`tab-btn-${tabName}`).className = "py-3 px-5 font-medium text-sm border-b-2 border-blue-600 text-blue-600 transition flex items-center space-x-2";
    }

    fetchState();
  </script>
</body>
</html>
"""

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif url.path == "/api/state":
            global learner_state
            data = {
                "profile": learner_state.get("profile", {}),
                "progress": learner_state.get("progress", {}),
                "activity_log": learner_state.get("activity_log", []),
                "last_analysis": learner_state.get("last_analysis", {}),
                "quizzes": quizzes_data,
                "roles": roles_data
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global learner_state
        url = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if url.path == "/api/demo":
            learner_state["profile"] = {
                "name": "Alex Chen",
                "target_role": "Full Stack Developer",
                "skills": ["Python", "SQL", "HTML & CSS"],
                "certifications": ["Python Essentials (Cisco)"],
                "projects": ["CLI Expense Tracker", "Database Query Tool"]
            }
            learner_state["progress"] = {"completed": [], "status_map": {}}
            learner_state["quiz_history"] = []
            res = orchestrator.handle_event("new_profile", learner_state, roles_data, quizzes_data)
            learner_state["last_analysis"] = res
            if "activity_log" not in learner_state:
                learner_state["activity_log"] = []
            for l in reversed(res.get("logs", [])):
                learner_state["activity_log"].insert(0, l)
            save_learner(learner_state)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        elif url.path == "/api/switch_role":
            new_role = payload.get("role", "Full Stack Developer")
            old_role = learner_state.get("profile", {}).get("target_role", "Full Stack Developer")
            learner_state["profile"]["target_role"] = new_role
            res = orchestrator.handle_event("goal_change", {
                "old_role": old_role,
                "new_role": new_role,
                "profile": learner_state["profile"]
            }, roles_data, quizzes_data)
            learner_state["last_analysis"] = res
            for l in reversed(res.get("logs", [])):
                learner_state["activity_log"].insert(0, l)
            save_learner(learner_state)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        elif url.path == "/api/save_profile":
            learner_state["profile"] = payload
            res = orchestrator.handle_event("new_profile", learner_state, roles_data, quizzes_data)
            learner_state["last_analysis"] = res
            for l in reversed(res.get("logs", [])):
                learner_state["activity_log"].insert(0, l)
            save_learner(learner_state)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        elif url.path == "/api/quiz":
            skill = payload.get("skill", "")
            answers = payload.get("answers", {})
            res = orchestrator.handle_event("quiz_result", {
                "skill": skill,
                "user_answers": answers,
                "profile": learner_state.get("profile", {}),
                "progress": learner_state.get("progress", {})
            }, roles_data, quizzes_data)
            learner_state["last_analysis"] = res
            learner_state["progress"] = res.get("updated_progress", learner_state.get("progress", {}))
            for l in reversed(res.get("logs", [])):
                learner_state["activity_log"].insert(0, l)
            save_learner(learner_state)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res.get("assessment", {})).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_server(port=8501):
    with socketserver.TCPServer(("", port), RequestHandler) as httpd:
        print(f"SkillForge AI running at http://localhost:{port}/")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server(8501)
