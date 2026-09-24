# NL-to-SQL Chat Assistant

## Overview

Build and deploy an end-to-end conversational AI assistant that translates natural language questions into SQL queries against a pharmaceutical sales database. The assistant must understand domain-specific business knowledge (provided in the `docs/` folder) to generate correct queries.

The end user — a commercial analytics user (sales rep, regional manager, or HQ analyst) — sees **only a chat interface**. They type a question in plain English, and the assistant responds with an answer. No SQL, no technical details visible to the user unless they ask.

## Time Estimate

**4–6 hours**

## The Data

The dataset models a fictional pharmaceutical company's commercial operations with four tables:

| Table | Rows | Description |
|-------|------|-------------|
| `organizations` | 40,000 | Master directory of healthcare facilities, hospitals, IDNs, GPOs |
| `sales` | 2,000,000 | ~3 years of daily sales transactions across multiple data sources |
| `products` | 40 | NDC-level drug reference with dosing and market classification |
| `zip_territory` | ~30,000 | ZIP code to sales territory and region mapping |

Run the data generator to produce CSVs:

```bash
python3 schema/generate_data.py
```

This creates CSV files in `schema/generated/`. Schema DDL is in `schema/create_tables.sql`. Use `schema/seed_data.sql` for a small sample to develop against locally before loading the full dataset.

> **Important:** Your solution must work with the full dataset at the scale above (40K organizations, 2M sales rows). This is not optional — your deployed application will be evaluated against the complete dataset. Design your database, queries, and infrastructure accordingly.

### Database Choice

You may use **any SQL database** for your solution — SQLite, PostgreSQL, MySQL, etc. NoSQL databases are out of scope. Choose whatever makes sense for your architecture. Load the generated CSVs into your database of choice.

## The Task

### 1. Chat Interface

Build a web-based chat UI that the end user interacts with. The user types natural language questions and receives answers. The interface should feel like a conversation — support follow-ups, show thinking/loading states, and present results clearly.

The user should **not** need to know SQL, understand the schema, or configure anything. Just open the URL and start asking questions.

### 2. NL-to-SQL Engine

Behind the chat interface, build a backend that:
1. Takes the user's natural language question
2. Generates a SQL query against the pharma database
3. Executes the query
4. Returns a natural language answer to the user

Think about what kinds of questions an analytics user would ask — aggregations, comparisons across time periods, rankings, multi-table joins — and make sure your system handles them well.

### 3. Domain Knowledge

The `docs/` folder contains business knowledge documents that define how metrics are calculated, what each data source means, how the organization hierarchy works, and how products are classified into markets.

A correct SQL query often depends on domain knowledge that isn't in the schema. For example, "market share" has a specific formula involving two different data sources, and "sales" implicitly means only paid demand — not free drug. Your assistant must incorporate this domain knowledge when generating SQL.

How you make this knowledge available to the assistant is up to you.

### 4. Security & Access Control

The system must enforce role-based access control. The `users` table (see `schema/seed_data.sql`) defines three roles:

| Role | Data Scope | WAC (Pricing) Access |
|------|-----------|---------------------|
| **Exec** | All territories, all regions | Full access |
| **Director** | All territories within their assigned region | **No access** — must be excluded from queries |
| **RAM** | Only their assigned territory | **No access** — must be excluded from queries |

**What this means:**
- A RAM in "New York Metro" should only see organizations and sales within that territory — never data from other territories
- A Director of the "Northeast" region sees all territories in that region (New York Metro + New England)
- An Exec sees everything
- WAC (wholesale acquisition cost) is sensitive pricing data. Only Execs can see it. Directors and RAMs must never see WAC values. If a non-Exec user asks a revenue question, the assistant should offer volume-based alternatives instead
- The chat interface must identify who is logged in and enforce these rules on every query

See `docs/security_model.md` for the full access control specification.

### 5. Cloud Deployment

Deploy the full solution to a **cloud provider** so that we can access it via a public URL. The deployed application must be fully functional — chat UI, backend, database, domain knowledge pipeline — all running in the cloud.

You choose the cloud provider and services. **AWS is preferred**, but GCP, Azure, or other cloud platforms are acceptable. Some AWS options to consider (not prescriptive):
- **Compute**: EC2, ECS/Fargate, Lambda, App Runner, Elastic Beanstalk
- **Database**: RDS, Aurora, or SQLite on EBS/EFS
- **Frontend**: S3 + CloudFront, Amplify, or served from the backend
- **Other**: Bedrock for LLM, OpenSearch for vector search, etc.

Include infrastructure setup instructions or IaC (Terraform, CDK, CloudFormation, Pulumi, etc.) in your repo.

## What We're Looking For

- **End-to-end delivery**: A working, deployed product accessible via URL — not just code on a laptop
- **Security**: Territory/region scoping enforced correctly, WAC hidden from non-Execs, no data leaks across roles
- **Correctness**: Does the system answer questions accurately? Does it apply domain knowledge correctly?
- **User experience**: Clean chat interface, clear answers, graceful error handling, multi-turn support
- **Domain knowledge integration**: How does the assistant leverage the business docs to produce correct SQL?
- **Architecture decisions**: Database choice, deployment strategy, prompt design, cost/performance trade-offs
- **Pragmatism**: Sensible trade-offs, clean code, clear documentation

## Constraints

- Use any LLM provider (OpenAI, Anthropic, AWS Bedrock, open-source, etc.)
- Use any SQL database (NoSQL is out of scope)
- Must be deployed to a cloud provider (AWS preferred) and accessible via a public URL
- Solution must be shared as a **GitHub repository**
- Include a `DESIGN.md` explaining your approach

## Deliverables

1. **GitHub repository** — all source code, IaC, and documentation
2. **Live URL** — the deployed chat application in the cloud
3. **`DESIGN.md`** — covering:
   - Architecture overview (diagram encouraged)
   - Database choice and rationale
   - How domain knowledge is integrated
   - LLM provider and prompt design
   - Security implementation — how access control is enforced (auth, query scoping, WAC restriction)
   - Cloud services used and why
   - Trade-offs made and what you'd improve with more time
4. **Test cases & results** — a document or test suite covering:
   - NL-to-SQL accuracy: sample questions, generated SQL, expected vs actual results
   - Security: queries from each role (Exec, Director, RAM) demonstrating correct data scoping and WAC restriction
   - Edge cases: ambiguous questions, invalid inputs, cross-territory access attempts
   - Include pass/fail status and actual output for each test case
5. **Demo** — a short screen recording (3–5 min) or transcript showing multi-turn conversations with the deployed app

## Questions?

If anything is unclear, document your assumptions in `DESIGN.md` and proceed. We value pragmatic decision-making over perfection.
