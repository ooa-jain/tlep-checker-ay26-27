import streamlit as st
import pandas as pd
import altair as alt

def is_pg(programme: str, course_title: str) -> bool:
    """Heuristic to determine if a course is UG or PG"""
    prog_lower = str(programme).lower()
    title_lower = str(course_title).lower()
    
    pg_keywords = ["m.", "master", "mba", "mca", "m.tech", "m.sc", "m.com", "m.des", "pg", "post graduate"]
    ug_keywords = ["b.", "bachelor", "bba", "bca", "b.tech", "b.sc", "b.com", "b.des", "ug", "under graduate"]
    
    for kw in pg_keywords:
        if kw in prog_lower or kw in title_lower:
            return True
    
    for kw in ug_keywords:
        if kw in prog_lower or kw in title_lower:
            return False
            
    return False # Default to UG if unknown

def render_batch_dashboard(results):
    """
    Renders a comprehensive Analytics Dashboard for a batch of audited courses.
    results: List of TLEPReviewResult objects.
    """
    if not results:
        st.warning("No audited courses available to generate dashboard.")
        return

    st.markdown("### 📊 Programme & Department Level Analytics")
    st.caption("Consolidated analytics for the uploaded batch.")
    
    # 1. Process Data
    data = []
    for r in results:
        level = "PG" if is_pg(getattr(r.normalized_tlep.course_info, 'programme', ''), getattr(r.normalized_tlep.course_info, 'course_title', '')) else "UG"
        data.append({
            "Course": r.normalized_tlep.course_info.course_title or r.file_name,
            "Code": r.normalized_tlep.course_info.course_code or "N/A",
            "Department": getattr(r.normalized_tlep.course_info, 'department', 'General'),
            "Programme": getattr(r.normalized_tlep.course_info, 'programme', 'General'),
            "Level": level,
            "Score": r.compliance_percentage,
            "Status": r.overall_status.value
        })
        
    df = pd.DataFrame(data)
    
    # 2. Top Level KPIs
    total_courses = len(df)
    avg_score = df["Score"].mean()
    compliant = len(df[df["Status"] == "Compliant"])
    needs_rev = len(df[df["Status"] == "Needs Revision"])
    major_rev = len(df[df["Status"].isin(["Major Revision", "Non-Compliant"])])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Courses", total_courses)
    col2.metric("Avg. Compliance", f"{avg_score:.1f}%")
    col3.metric("Fully Compliant", compliant)
    col4.metric("Requires Rework", major_rev)
    
    st.divider()
    
    # 3. Charts Row 1: Status Distribution & UG/PG Split
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("**Compliance Status Distribution**")
        status_counts = df["Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        
        chart1 = alt.Chart(status_counts).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Count", type="quantitative"),
            color=alt.Color(field="Status", type="nominal", 
                            scale=alt.Scale(domain=["Compliant", "Needs Revision", "Major Revision", "Non-Compliant"],
                                            range=["#16A34A", "#CA8A04", "#DC2626", "#991B1B"])),
            tooltip=["Status", "Count"]
        ).properties(height=300)
        st.altair_chart(chart1, use_container_width=True)
        
    with c2:
        st.markdown("**UG vs PG Course Distribution**")
        level_counts = df["Level"].value_counts().reset_index()
        level_counts.columns = ["Level", "Count"]
        
        chart2 = alt.Chart(level_counts).mark_bar().encode(
            x=alt.X('Level', title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y('Count', title='Number of Courses'),
            color=alt.Color('Level', legend=None, scale=alt.Scale(domain=["UG", "PG"], range=["#2563EB", "#7C3AED"])),
            tooltip=["Level", "Count"]
        ).properties(height=300)
        st.altair_chart(chart2, use_container_width=True)

    # 4. Charts Row 2: Department Performance
    st.markdown("**Average Compliance Score by Department**")
    dept_scores = df.groupby("Department")["Score"].mean().reset_index()
    dept_scores.columns = ["Department", "Average Score"]
    dept_scores = dept_scores.sort_values("Average Score", ascending=False)
    
    chart3 = alt.Chart(dept_scores).mark_bar(color="#0EA5E9").encode(
        x=alt.X('Average Score', title='Average Compliance (%)', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y('Department', sort='-x', title=None),
        tooltip=["Department", alt.Tooltip("Average Score", format=".1f")]
    ).properties(height=max(300, len(dept_scores) * 30))
    
    st.altair_chart(chart3, use_container_width=True)
    
    # 5. Data Table
    with st.expander("View Complete Course Audit Roster"):
        st.dataframe(df.style.background_gradient(subset=['Score'], cmap='RdYlGn', vmin=0, vmax=100), use_container_width=True)
