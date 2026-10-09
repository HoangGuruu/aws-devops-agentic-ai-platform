# Claude for Startups: application draft

Apply at: https://platform.claude.com/offers/startups-application (sign in to the Claude Console first).

The exact form fields are not published, so the answers below are written for the usual questions: company, product, how you use Claude, expected usage, and stage. Copy the parts that fit each field. Items in [BRACKETS] need your own information. Do not invent numbers; use real ones.

---

## Company / project name
[Your company or brand name], a community DevOps education project

## One-line description
An open, hands-on community course that teaches DevOps on AWS, from containers and Kubernetes to GitOps and incident response, with a Claude-powered AI investigator that helps learners diagnose and recover from real production-style incidents.

## What are you building?
We are building an open-source, step-by-step lab course, "DevOps on AWS & AI", and growing it into a community course. Learners deploy a real application (Bookinfo) to AWS using Docker, Terraform, EKS, Argo CD and GitHub Actions. They then monitor it, break it on purpose, and recover it through Git.

The course already has 12 lessons, a working Python agent, tests, and a published Udemy edition. We are now expanding it into a community course for people who already know the basics of DevOps but find the AWS and Kubernetes learning curve steep.

Repository: https://github.com/hoangguruu/aws-devops-agentic-ai-platform
Course: https://www.udemy.com/course/devops-on-aws-real-project-all-in-one/

## How will you use Claude?
Claude is the core of the AI half of the course, and we are moving it to the Claude API:

1. **AI incident investigator.** A tool-using agent that gets read-only access to a Kubernetes cluster, reads logs, events and metrics, searches runbooks, and writes an investigation report. Learners see how tool use, least-privilege permissions and guardrails work in practice.
2. **Approved recovery proposals.** Claude proposes a fix, a human reviews it, and the fix is applied through Git and verified. This teaches human-in-the-loop AI operations.
3. **Runbook knowledge (RAG).** Claude answers from the course runbooks and learner documentation.
4. **Learning assistant.** Claude Code and Claude help beginners at each lesson: explaining errors, reviewing Terraform and Kubernetes manifests, and suggesting next steps. We also ship a CLAUDE.md and project skills so learners can work with Claude Code on the repo.

The agent currently calls models through a cloud provider's hosted service. We are replacing that with the Claude API through the Console, because it gives learners a simpler setup (one API key, no cloud model-access approvals) and keeps the lab inexpensive.

## Why Claude?
- Reliable tool use is essential for an agent that must call read-only cluster tools safely.
- Strong reasoning over logs, manifests and infrastructure code.
- Claude Code gives learners a practical way to work on real DevOps repositories.

## Who benefits?
Engineers who know basic DevOps and want to move to AWS, Kubernetes and AI-assisted operations. The course is open, step by step, and designed so each lesson says what to change, why, which command to run, and what to expect.

## Stage and funding
[Bootstrapped / pre-seed. Fill in: company registration status, year founded, any investors.]
Current traction: [real numbers, e.g. Udemy students, GitHub stars, community size].

## Expected API usage
[Estimate honestly. Example: "Each learner runs the investigator roughly 20 to 50 times through the course, with short prompts and tool results. We expect [N] active learners in the first six months." Add the models you plan to use.]

How credits will be used: development and testing of the agent and labs, a free demo tier for community learners, and automated tests run against the live API.

## Team
[Your name], course author and DevOps engineer. [Role, background, LinkedIn.]

## Website / contact
[Landing page URL]. Use an email on the same domain as the website.
