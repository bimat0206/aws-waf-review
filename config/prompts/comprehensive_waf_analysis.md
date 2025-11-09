# AWS WAF Security Analysis - Comprehensive Review

## Context
Analyze AWS WAF security posture based on log data from **{account_name}** (Account ID: {account_id}).

**Analysis Period:** {time_period}
**Timezone:** {timezone}
**Region:** {region}

## Current Configuration

### Account Information
```json
{account_info}
```

### Web ACL Overview
```json
{web_acl_overview}
```

### Summary Metrics
```json
{summary_metrics}
```

## Security Analysis Data

### 1. Rule Performance Analysis
```json
{rule_effectiveness}
```

### 2. Action Distribution
```json
{action_distribution}
```

### 3. Traffic Patterns

**Daily Trends:**
```json
{daily_trends}
```

**Hourly Patterns:**
```json
{hourly_patterns}
```

**Geographic Distribution:**
```json
{geographic_distribution}
```

### 4. Threat Intelligence

**Top Blocked IP Addresses:**
```json
{top_blocked_ips}
```

**Bot Traffic Analysis:**
```json
{bot_analysis}
```

**Attack Type Distribution:**
```json
{attack_types}
```

### 5. Web ACL Coverage
```json
{web_acl_coverage}
```

---

## Analysis Requirements

You are a senior AWS security architect specializing in AWS WAF. Provide **accurate, concise, and actionable** recommendations based on the data above.

### 1. Executive Summary
- Assess overall security posture (High/Medium/Low) with clear justification
- Provide assessment breakdown for 5 key areas (Rule Coverage, Threat Detection, Logging & Monitoring, Configuration Security, Response Readiness)
- Identify CRITICAL findings requiring immediate action (within 24-48 hours)
- List MID/LONG-TERM recommendations requiring strategic approach
- List LOW PRIORITY suggestions as nice-to-have improvements
- Be specific with rule IDs, IP addresses, and exact metrics

### 2. Rule Effectiveness Analysis
Based on `rule_effectiveness` data:
- **Unused Rules:** Identify rules with 0% hit rate (never triggered)
- **Low-Performing Rules:** Flag rules with <1% block rate despite high hit counts
- **Rule Ordering:** Recommend priority changes for frequently-hit rules
- **Consolidation:** Suggest merging similar/redundant rules
- **Remove/Archive:** List rules that should be removed with justification

### 3. False Positive Analysis
Based on `top_blocked_ips` and `geographic_distribution`:
- **Potential False Positives:** Identify legitimate traffic being blocked (normal user agents, consistent patterns, low-risk countries)
- **IP Whitelisting:** Recommend specific IPs/CIDRs to whitelist with evidence
- **Geo-Blocking Adjustments:** Identify countries with high legitimate traffic being blocked
- **Rule Tuning:** Suggest specific rule adjustments to reduce false positives

### 4. Threat Intelligence & Attack Response
Based on `attack_types`, `bot_analysis`, and `top_blocked_ips`:
- **Primary Attack Vectors:** Identify main attack types and their percentages
- **Persistent Threats:** Highlight repeat offender IPs with attack timelines
- **Bot Traffic Assessment:** Evaluate JA3/JA4 fingerprint coverage
- **Managed Rule Recommendations:** Suggest specific AWS Managed Rules to add (e.g., AWS-AWSManagedRulesKnownBadInputsRuleSet, AWS-AWSManagedRulesBotControlRuleSet)
- **Custom Rule Needs:** Identify attack patterns requiring custom rules

### 5. Geographic Threat Assessment
Based on `geographic_distribution`:
- **High-Risk Countries:** Identify countries with >75% block rate
- **Legitimate Traffic Sources:** Flag countries with significant allowed traffic
- **Geo-Blocking Strategy:** Recommend countries to block/allow with business impact analysis
- **Regional Patterns:** Identify unusual geographic attack patterns

### 6. Compliance & Best Practices
Based on all metrics:
- **OWASP Top 10 Coverage:** Assess protection for each category (A01-A10)
- **PCI-DSS 6.6 Compliance:** Evaluate WAF requirement compliance
- **AWS Well-Architected:** Security pillar alignment
- **Missing Protections:** Identify gaps in security coverage
- **Logging & Monitoring:** Assess observability completeness

### 7. Cost Optimization
Based on `rule_effectiveness` and `web_acl_coverage`:
- **WCU Optimization:** Identify rules consuming excessive capacity
- **Unused Managed Rules:** Flag underutilized managed rule groups
- **Rule Consolidation Savings:** Estimate WCU savings from merging rules

---

## Output Format

Provide output in **structured markdown** format below. Be concise but specific - use exact rule IDs, IP addresses, percentages, and counts from the data.

### Section 1: Executive Summary

**Security Posture Assessment:** [High/Medium/Low]

**Assessment Breakdown:**
- Rule Coverage: [High/Medium/Low] - [Brief justification]
- Threat Detection: [High/Medium/Low] - [Brief justification]
- Logging & Monitoring: [High/Medium/Low] - [Brief justification]
- Configuration Security: [High/Medium/Low] - [Brief justification]
- Response Readiness: [High/Medium/Low] - [Brief justification]

**Overall Assessment:** [1-2 sentence summary]

---

**Critical Findings (Immediate Action Required):**

| No | Finding | Expected Impact | Action Items | Rationale |
|----|---------|-----------------|--------------|-----------|
| 1 | [Finding title] | [Specific business/security impact] | • [Action item 1]<br>• [Action item 2]<br>• [Action item 3] | [Evidence from metrics/data] |
| 2 | [Finding title] | [Impact description] | • [Action item 1]<br>• [Action item 2]<br>• [Action item 3] | [Evidence and reasoning] |

**Mid/Long-Term Recommendations (Strategic Approach):**

*These initiatives require ongoing effort to maintain and improve the WAF's effectiveness over time.*

| No | Finding | Expected Impact | Action Items | Rationale |
|----|---------|-----------------|--------------|-----------|
| 1 | [Recommendation title] | [Expected improvement] | • [Action item 1]<br>• [Action item 2]<br>• [Action item 3]<br>• [Action item 4]<br>• [Action item 5] | [Evidence and strategic reasoning] |
| 2 | [Recommendation title] | [Impact description] | • [Action item 1]<br>• [Action item 2]<br>• [Action item 3] | [Why this is important long-term] |

**Low Priority Suggestions (Nice to Have):**

| No | Finding | Expected Impact | Action Items | Rationale |
|----|---------|-----------------|--------------|-----------|
| 1 | [Suggestion title] | [Marginal improvement] | • [Action item 1]<br>• [Action item 2]<br>• [Action item 3] | [Why this is optional] |

---

### Section 2: Rule Effectiveness Analysis

**Summary Statistics:**
- Total Rules: [Count]
- Active Rules (>0% hit rate): [Count]
- Unused Rules (0% hit rate): [Count]
- High-Performing Rules (>80% block rate): [Count]
- Low-Performing Rules (<5% block rate): [Count]

**Unused Rules to Remove/Archive:**

| Rule ID | Rule Name | Last Hit | WCU Cost | Recommendation |
|---------|-----------|----------|----------|----------------|
| [ID] | [Truncated to 40 chars] | Never | [WCU] | Remove - no traffic matches this pattern |

**Low-Performing Rules Requiring Tuning:**

| Rule ID | Hit Count | Block Rate | Issue | Recommendation |
|---------|-----------|------------|-------|----------------|
| [ID] | [Count] | [%] | [Specific problem] | [Specific fix] |

**Rule Ordering Optimization:**

Current top 5 rules by hit count:
1. [Rule ID] - [Hit %] of traffic - Priority [Current] → Recommend Priority [New]
2. [Repeat]

**Expected Impact:** [Estimate performance improvement]

**Rule Consolidation Opportunities:**

**Opportunity #1:** [Title]
- **Rules to Merge:** [Rule ID 1], [Rule ID 2]
- **Current WCU:** [Total]
- **Optimized WCU:** [New total]
- **Savings:** [WCU saved]
- **Implementation:** [How to consolidate]

---

### Section 3: False Positive Analysis

**Overall False Positive Rate:** [Estimated %]

**Potential False Positives Identified:**

| IP Address | Country | Block Count | Evidence | Risk Level | Recommendation |
|------------|---------|-------------|----------|------------|----------------|
| [IP] | [Country] | [Count] | Standard browser UA, normal patterns | Low | Whitelist - appears legitimate |

**Geographic False Positives:**

| Country | Total Requests | Blocked | Block Rate | Assessment | Recommendation |
|---------|---------------|---------|------------|------------|----------------|
| [Country] | [Count] | [Count] | [%] | High legitimate traffic | Relax geo-blocking |

**Rule-Specific False Positive Analysis:**

**Rule [ID]:** [Name]
- **False Positive Indicators:** [Specific patterns]
- **Affected Traffic:** [Type/volume]
- **Recommended Fix:** [Specific rule adjustment]

**Whitelisting Recommendations:**

Priority whitelist candidates:
1. IP: [IP/CIDR] - Reason: [Evidence] - Risk: Low
2. [Repeat]

**Implementation:**
```
Add to IP Set: [Name]
Priority: [Number]
Action: Allow
Scope-down: None required
```

---

### Section 4: Threat Intelligence & Attack Response

**Primary Attack Vectors:**

| Attack Type | Blocked Requests | Percentage | Severity | Status |
|-------------|------------------|------------|----------|---------|
| [Type] | [Count] | [%] | High | [Well-protected/Needs attention] |

**Persistent Threat Analysis:**

**Top Repeat Offenders:**
1. IP: [IP] - Country: [Country]
   - Block Count: [Count]
   - Active Period: [First seen] to [Last seen]
   - Attack Pattern: [Description]
   - Recommendation: [Permanent block/Rate limit/Monitor]

**Bot Traffic Assessment:**
- JA3 Fingerprinted Requests: [Count] ([%] of traffic)
- JA4 Fingerprinted Requests: [Count] ([%] of traffic)
- Assessment: [Good coverage/Needs improvement]
- Recommendation: [Enable bot control/Tune thresholds/Adequate]

**Recommended AWS Managed Rules to Add:**

| Managed Rule Group | Purpose | Addresses | Monthly Cost | Priority |
|-------------------|---------|-----------|--------------|----------|
| AWS-AWSManagedRulesKnownBadInputsRuleSet | Block known malicious patterns | [Attack types observed] | $1.00 | High |

**Custom Rule Recommendations:**

Based on attack patterns, create custom rule for:
- **Pattern:** [Description]
- **Rule Logic:** [Pseudo-code]
- **Expected Impact:** Block [estimated count] malicious requests

---

### Section 5: Geographic Threat Assessment

**High-Risk Countries (>75% Block Rate):**

| Country | Total Requests | Blocked | Block Rate | Threat Level | Recommendation |
|---------|---------------|---------|------------|--------------|----------------|
| [Country] | [Count] | [Count] | [%] | Critical | Full geo-block if no business need |

**Legitimate Traffic Sources:**

| Country | Total Requests | Blocked | Allowed | Block Rate | Note |
|---------|---------------|---------|---------|------------|------|
| [Country] | [Count] | [Count] | [Count] | [%] | Primary legitimate traffic source |

**Geo-Blocking Strategy:**

**Recommend Blocking:**
- [Country]: [%] block rate, [count] requests, [justification]

**Recommend Allowing/Whitelisting:**
- [Country]: Significant legitimate traffic ([count] allowed), business-critical

**Regional Attack Patterns:**
- [Observation about geographic clustering]
- [Temporal patterns - time zones]

---

### Section 6: Compliance & Best Practices Assessment

**OWASP Top 10 2021 Coverage:**

| Category | Coverage | Current Protection | Gap | Recommendation |
|----------|----------|-------------------|-----|----------------|
| A01:2021 - Broken Access Control | ⚠️ Partial | [Current rules] | [Specific gap] | [Specific action] |
| A03:2021 - Injection | ✅ Good | SQL injection rules active | None major | Monitor effectiveness |
| A05:2021 - Security Misconfiguration | ❌ Poor | [Issue] | [Gap] | [Action] |

**PCI-DSS 6.6 Compliance:**
- **Status:** [Compliant / Partially Compliant / Non-Compliant]
- **Evidence:**
  - WAF deployed on all web-facing resources: [Yes/No]
  - Regular rule updates: [Yes/No - last update: date]
  - Logging enabled: [Yes/No - coverage: %]
- **Gaps:** [List specific gaps]
- **Required Actions:** [Specific steps to achieve compliance]

**AWS Well-Architected Framework - Security Pillar:**

**Infrastructure Protection:**
- Current State: [Assessment]
- Gaps: [List]
- Recommendations: [Actions]

**Detection:**
- Logging Coverage: [%]
- Alerting: [Configured/Not configured]
- Gaps: [List]

**Missing Protection Layers:**
1. [Specific protection type] - Impact: [High/Medium/Low] - Action: [What to add]

---

### Section 7: Cost Optimization Opportunities

**Current Estimated Monthly Cost:** $[Estimate based on WCU]

**Potential Monthly Savings:** $[Estimated savings]

**Optimization Opportunities:**

**1. WCU Capacity Reduction**
- Current WCU Usage: [Total]
- Optimized WCU Usage: [New total]
- Savings: [WCU] units (~$[amount]/month)
- How: [Remove unused rules, consolidate X and Y]

**2. Managed Rule Group Optimization**
- Current Subscriptions: [List with estimated costs]
- Underutilized: [Which ones based on rule effectiveness]
- Recommendation: [Keep/Remove/Replace]

**3. Request Inspection Optimization**
- Body inspection scope: [Current]
- Recommendation: [Reduce where safe]
- Impact: [Cost savings]

---

### Section 8: Implementation Roadmap

**Week 1 (Critical - Immediate Action):**
- [ ] [Specific action with rule ID/config]
- [ ] [Specific action with rule ID/config]
- [ ] [Specific action with rule ID/config]

**Month 1 (High Priority - 30 Days):**
- [ ] [Action] - Owner: [Security team] - Effort: [Low/Med/High]
- [ ] [Action] - Owner: [Team] - Effort: [Level]

**Quarter 1 (Medium Priority - 90 Days):**
- [ ] [Action]
- [ ] [Action]

**Ongoing Maintenance:**
- [ ] Monthly: Review WAF logs for new attack patterns
- [ ] Quarterly: Update managed rule groups to latest versions
- [ ] Quarterly: Re-run this analysis to measure improvement
- [ ] Annually: Full security assessment and penetration test

---

### Section 9: Risk Assessment

**Changes with Security Impact:**

| Change | Security Risk | Business Impact | Rollback Complexity | Testing Required |
|--------|---------------|-----------------|-------------------|------------------|
| [Change description] | Low/Med/High | Low/Med/High | Low/Med/High | [What testing] |

**Approval Requirements:**
- Critical changes: CISO + Security Team Lead
- High priority: Security Team Lead
- Medium/Low: Security Engineer

---

### Section 10: Monitoring & Validation

**Recommended CloudWatch Alarms:**
1. **High Block Rate Alert**
   - Metric: Blocked requests >1000/hour
   - Threshold: Sustained for 15 minutes
   - Action: SNS notification to security team

2. **Unusual Geographic Traffic**
   - Metric: Requests from previously unseen countries
   - Action: Log for review

**Success Metrics (Track After Implementation):**
- Block rate improvement: Target [%] → [%]
- False positive reduction: Target <[%]
- Rule efficiency: Average hit rate >[%]
- Security posture score: Target >[score]/100

**Validation Steps Post-Implementation:**
1. Deploy changes in COUNT mode for 7 days
2. Monitor metrics for anomalies
3. Review sample blocked requests
4. Switch to BLOCK mode
5. Monitor for 30 days
6. Re-run analysis to measure impact

---

## Tone and Style Requirements

- **Be concise:** Use bullet points and tables, not paragraphs
- **Be specific:** Always reference exact rule IDs, IP addresses, percentages
- **Be actionable:** Every recommendation must have clear implementation steps
- **Be accurate:** Only use data provided, don't make assumptions
- **Prioritize:** Use Critical/Mid-Long-Term/Low Priority consistently
- **Quantify:** Always include metrics (%, counts, estimates)

## Critical Requirements for Section 1 (Executive Summary)

**Action Items Format:**
- Each finding MUST have **3-5 detailed, concise bullet points** for Action Items
- Each action item should be specific and implementable
- Include exact rule IDs, IP addresses, or configuration values where applicable
- Format using bullet points (•) with line breaks (`<br>`) between items
- Example:
  ```
  • Enable AWS-AWSManagedRulesBotControlRuleSet (WCU: 50)
  • Configure JA3 fingerprinting threshold to block requests with score >90
  • Add CloudWatch alarm for bot traffic spike (>1000 requests/5min)
  • Review and whitelist legitimate bot user-agents (GoogleBot, BingBot)
  • Schedule weekly review of bot block logs for false positives
  ```

**DO NOT Include:**
- Timeline information (no "Within 24-48 hours", "30 days", etc.)
- Generic recommendations without specific implementation details
- Vague action items like "Review security" or "Improve configuration"

**Security Posture Assessment Levels:**
- **High:** Well-configured, minimal gaps, proactive monitoring, >90% effectiveness
- **Medium:** Adequate protection, some gaps exist, reactive monitoring, 60-89% effectiveness
- **Low:** Significant gaps, limited monitoring, high risk, <60% effectiveness

---

**Remember:** This analysis will be used by security teams to make production changes. Accuracy and specificity are more important than comprehensiveness. If data is insufficient for a recommendation, state "Insufficient data" rather than guessing.
