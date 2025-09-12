# Week 3 — Human-Readable Explanations Review Guide

## Overview
This guide helps reviewers evaluate Orca Core's human-readable explanation system for Week 3. The goal is to ensure explanations are clear, accurate, and useful for both merchants and developers.

## 5-Minute Review Script

### Step 1: Setup (1 minute)
1. Open the Streamlit app: `streamlit run apps/explain/app_streamlit.py`
2. Download one of the example files from the sidebar
3. Upload the example file to see the decision and explanation

### Step 2: Review Process (3 minutes)
1. Look at the **Human Explanation** section
2. Compare it to the **Reasons** list
3. Check if the explanation matches the decision status
4. Consider if the explanation would be helpful to a customer

### Step 3: Test Different Scenarios (1 minute)
1. Try uploading different example files
2. Notice how explanations change based on different reasons
3. Check for consistency in explanation style

## 6 Key Review Questions

### 1. Is the explanation clear?
**What to look for:**
- Easy to understand language
- No technical jargon
- Clear cause and effect
- Appropriate level of detail

**Example to evaluate:**
- ✅ Good: "Declined: Amount exceeds card threshold of $5,000"
- ❌ Poor: "Declined: HIGH_TICKET rule triggered with threshold violation"

### 2. Does it match the JSON reasons?
**What to look for:**
- Explanation covers all the reasons listed
- No contradictions between explanation and reasons
- Consistent decision status

**Example to evaluate:**
- Reasons: `["velocity_flag", "location_mismatch"]`
- ✅ Good: "Declined: Too many recent attempts. Additionally, unusual location detected."
- ❌ Poor: "Declined: Transaction rejected" (too vague)

### 3. What's missing to trust this?
**What to look for:**
- Specific thresholds or limits mentioned
- Clear next steps for the user
- Confidence indicators
- Contact information for support

**Example to evaluate:**
- ✅ Good: "Declined: Amount exceeds ACH limit of $2,000. Please try a smaller amount or use a different payment method."
- ❌ Poor: "Declined: ACH limit exceeded."

### 4. Would this reduce your support time?
**What to look for:**
- Self-explanatory explanations
- Clear action items for users
- Reduces need for customer service calls
- Helps users understand what to do next

**Example to evaluate:**
- ✅ Good: "Under review: Additional verification required. Please check your email for verification instructions."
- ❌ Poor: "Under review: Manual review required."

### 5. Any terms that are jargon/confusing?
**What to look for:**
- Technical terms explained in plain language
- Industry jargon avoided
- Clear terminology for different user types

**Example to evaluate:**
- ✅ Good: "Bank transfer limit exceeded"
- ❌ Poor: "ACH limit exceeded" (without explanation)

### 6. What else would you want to see?
**What to look for:**
- Additional context that would be helpful
- Missing information that users typically need
- Suggestions for improvement

**Example to evaluate:**
- ✅ Good: "Declined: Too many recent attempts (last 24h: 5 transactions). Please wait 2 hours before trying again."
- ❌ Poor: "Declined: Velocity exceeded."

## Sample Scenarios to Test

### Scenario 1: Card High Ticket
**File:** `fixtures/week3/requests/card_decline_velocity.json`
**Expected:** Velocity-based decline explanation
**Focus:** Check if explanation mentions transaction frequency

### Scenario 2: ACH Limit Exceeded
**File:** `fixtures/week3/requests/ach_decline_limit.json`
**Expected:** ACH limit explanation
**Focus:** Check if explanation mentions the $2,000 limit

### Scenario 3: Multiple Reasons
**File:** `fixtures/week3/requests/combined_signals_sample.json` (if available)
**Expected:** Multiple reason explanation
**Focus:** Check if all reasons are covered clearly

## Review Checklist

### ✅ Excellent
- [ ] Clear, non-technical language
- [ ] Matches all reasons in JSON
- [ ] Provides specific thresholds/limits
- [ ] Gives clear next steps
- [ ] Consistent style across scenarios
- [ ] Would reduce support calls

### ⚠️ Needs Improvement
- [ ] Some technical terms unclear
- [ ] Missing some details from reasons
- [ ] Vague about next steps
- [ ] Inconsistent formatting
- [ ] Might still generate support calls

### ❌ Poor
- [ ] Too technical/jargon-heavy
- [ ] Doesn't match reasons
- [ ] No actionable guidance
- [ ] Confusing or contradictory
- [ ] Would increase support burden

## Feedback Format

Please provide feedback in this format:

```
**Reviewer:** [Name/Role]
**Date:** [Date]
**Scenario Tested:** [Which files you tested]

**Question 1 - Clarity:** [Rating: ✅/⚠️/❌]
[Specific comments about clarity]

**Question 2 - Accuracy:** [Rating: ✅/⚠️/❌]
[Comments about matching reasons]

**Question 3 - Trust:** [Rating: ✅/⚠️/❌]
[What's missing for trust]

**Question 4 - Support:** [Rating: ✅/⚠️/❌]
[Impact on support time]

**Question 5 - Jargon:** [Rating: ✅/⚠️/❌]
[Confusing terms identified]

**Question 6 - Improvements:** [Rating: ✅/⚠️/❌]
[Additional suggestions]

**Overall Rating:** [✅/⚠️/❌]
**Key Strengths:**
- [Strength 1]
- [Strength 2]

**Key Issues:**
- [Issue 1]
- [Issue 2]

**Recommendations:**
- [Recommendation 1]
- [Recommendation 2]
```

## Next Steps

1. **Complete the review** using this guide
2. **Submit feedback** via the feedback form or email
3. **Wait for improvements** based on feedback
4. **Re-test** after improvements are made

## Contact

For questions about this review process, contact the Orca Core team or refer to the project documentation.
