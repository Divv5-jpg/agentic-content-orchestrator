import streamlit as st
from bwa_backend import app


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="BWA — Blog Writing Agent",
    page_icon="✦",
    layout="wide",
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("✦ BWA")
    st.caption("Blog Writing Agent")

    st.divider()

    st.subheader("Create")

    topic = st.text_area(
        "What should I write about?",
        placeholder=(
            "e.g. Explain self-attention in "
            "Transformer architecture"
        ),
        height=120,
    )

    st.divider()

    st.subheader("Generation")

    st.info(
        "The router automatically decides whether "
        "web research is required."
    )

    generate_button = st.button(
        "✦ Generate Blog",
        type="primary",
        use_container_width=True,
    )


# ============================================================
# MAIN HEADER
# ============================================================

st.title("Turn an idea into a publication-ready blog.")

st.write(
    "A LangGraph-powered writing system that plans, "
    "researches, writes and organizes evidence "
    "from a single topic."
)


# ============================================================
# EMPTY STATE
# ============================================================

if not generate_button:

    st.divider()

    st.info(
        "Enter a topic in the sidebar and click "
        "**Generate Blog** to start."
    )

    st.markdown("### How it works")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("1", "Router")
        st.caption(
            "Decides whether research is needed."
        )

    with col2:
        st.metric("2", "Research")
        st.caption(
            "Collects relevant evidence when required."
        )

    with col3:
        st.metric("3", "Workers")
        st.caption(
            "Five workers write the planned sections."
        )

    with col4:
        st.metric("4", "Reducer")
        st.caption(
            "Combines the sections into one blog."
        )

    st.stop()


# ============================================================
# VALIDATE TOPIC
# ============================================================

if not topic.strip():

    st.error(
        "Please enter a topic in the sidebar first."
    )

    st.stop()


# ============================================================
# INITIAL GRAPH STATE
# ============================================================

inputs = {
    "topic": topic.strip(),
    "mode": "",
    "needs_research": False,
    "queries": [],
    "evidence": [],
    "plan": None,
    "sections": [],
    "final": "",
}


# ============================================================
# RUN GRAPH
# ============================================================

st.divider()

st.subheader("Generating your blog")

final_state = None

try:

    with st.status(
        "Running the blog generation pipeline...",
        expanded=True,
    ) as status:

        for state in app.stream(
            inputs,
            stream_mode="values",
        ):

            final_state = state

            # --------------------------------------------
            # Router
            # --------------------------------------------

            if state.get("mode"):

                mode = state["mode"]

                if mode == "closed_book":

                    st.write(
                        "🔀 Router: closed-book mode"
                    )

                elif mode == "open_book":

                    st.write(
                        "🔀 Router: open-book research"
                    )

                elif mode == "hybrid":

                    st.write(
                        "🔀 Router: hybrid research"
                    )


            # --------------------------------------------
            # Research
            # --------------------------------------------

            if state.get("queries"):

                st.write(
                    "🔎 Research queries generated:"
                )

                for query in state["queries"]:

                    st.write(
                        f"- {query}"
                    )


            # --------------------------------------------
            # Evidence
            # --------------------------------------------

            evidence = state.get(
                "evidence",
                [],
            )

            if evidence:

                st.write(
                    f"📚 Evidence collected: "
                    f"{len(evidence)} sources"
                )


            # --------------------------------------------
            # Plan
            # --------------------------------------------

            plan = state.get("plan")

            if plan is not None:

                st.write(
                    f"🧠 Plan created: "
                    f"{len(plan.tasks)} sections"
                )


            # --------------------------------------------
            # Workers
            # --------------------------------------------

            sections = state.get(
                "sections",
                [],
            )

            if sections:

                st.write(
                    f"✍️ Sections completed: "
                    f"{len(sections)}/5"
                )


            # --------------------------------------------
            # Final
            # --------------------------------------------

            if state.get("final"):

                st.write(
                    "✅ Blog assembled successfully."
                )


        status.update(
            label="Blog generation complete",
            state="complete",
            expanded=False,
        )


except Exception as e:

    st.error(
        "An error occurred while generating the blog."
    )

    st.exception(e)

    st.stop()


# ============================================================
# CHECK RESULT
# ============================================================

if final_state is None:

    st.error(
        "The backend did not return a result."
    )

    st.stop()


# ============================================================
# GET OUTPUT
# ============================================================

plan = final_state.get("plan")

evidence = final_state.get(
    "evidence",
    [],
)

sections = final_state.get(
    "sections",
    [],
)

final_md = final_state.get(
    "final",
    "",
)

mode = final_state.get(
    "mode",
    "",
)

needs_research = final_state.get(
    "needs_research",
    False,
)


# ============================================================
# SUMMARY
# ============================================================

st.divider()

st.subheader("Generation Summary")

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Sections",
        len(plan.tasks) if plan else 0,
    )


with col2:

    st.metric(
        "Sources",
        len(evidence),
    )


with col3:

    word_count = len(
        final_md.split()
    )

    st.metric(
        "Words",
        word_count,
    )


with col4:

    if mode:
        display_mode = mode.replace(
            "_",
            " ",
        ).title()
    else:
        display_mode = "Unknown"

    st.metric(
        "Research Mode",
        display_mode,
    )


# ============================================================
# TABS
# ============================================================

tab_blog, tab_plan, tab_research, tab_pipeline = st.tabs(
    [
        "📖 Blog",
        "🧠 Plan",
        "🔎 Research",
        "⚙️ Pipeline",
    ]
)


# ============================================================
# BLOG TAB
# ============================================================

with tab_blog:

    st.subheader("Generated Blog")

    if final_md:

        st.markdown(final_md)

        st.divider()

        st.download_button(
            label="⬇️ Download Markdown",
            data=final_md,
            file_name="generated_blog.md",
            mime="text/markdown",
            use_container_width=True,
        )

    else:

        st.warning(
            "No final blog was returned by the backend."
        )


# ============================================================
# PLAN TAB
# ============================================================

with tab_plan:

    st.subheader("Blog Plan")

    if plan is None:

        st.warning(
            "No plan was returned."
        )

    else:

        st.write(
            f"**Title:** {plan.blog_title}"
        )

        st.write(
            f"**Audience:** {plan.audience}"
        )

        st.write(
            f"**Tone:** {plan.tone}"
        )

        st.write(
            f"**Blog type:** {plan.blog_kind}"
        )

        if plan.constraints:

            st.write("**Constraints:**")

            for constraint in plan.constraints:

                st.write(
                    f"- {constraint}"
                )

        st.divider()

        st.subheader(
            f"Sections ({len(plan.tasks)})"
        )

        for task in plan.tasks:

            with st.container(border=True):

                st.write(
                    f"### {task.id} — {task.title}"
                )

                st.write(
                    f"**Goal:** {task.goal}"
                )

                st.write(
                    f"**Target words:** "
                    f"{task.target_words}"
                )

                st.write("**Topics covered:**")

                for bullet in task.bullets:

                    st.write(
                        f"- {bullet}"
                    )

                col_a, col_b, col_c = st.columns(3)

                with col_a:

                    st.write(
                        f"Research: "
                        f"{'Yes' if task.requires_research else 'No'}"
                    )

                with col_b:

                    st.write(
                        f"Citation: "
                        f"{'Yes' if task.requires_citation else 'No'}"
                    )

                with col_c:

                    st.write(
                        f"Code: "
                        f"{'Yes' if task.requires_code else 'No'}"
                    )


# ============================================================
# RESEARCH TAB
# ============================================================

with tab_research:

    st.subheader("Research")

    if needs_research:

        st.success(
            "The router determined that web research is required."
        )

    else:

        st.info(
            "The router determined that web research "
            "is not required."
        )


    if mode:

        st.write(
            f"**Mode:** {mode}"
        )


    # --------------------------------------------
    # Queries
    # --------------------------------------------

    queries = final_state.get(
        "queries",
        [],
    )

    if queries:

        st.subheader("Queries")

        for query in queries:

            st.write(
                f"- {query}"
            )


    # --------------------------------------------
    # Evidence
    # --------------------------------------------

    st.subheader(
        f"Evidence ({len(evidence)})"
    )

    if not evidence:

        st.info(
            "No research evidence was collected."
        )

    else:

        for i, item in enumerate(
            evidence,
            start=1,
        ):

            with st.container(border=True):

                st.write(
                    f"**{i}. {item.title}**"
                )

                if item.source:

                    st.caption(
                        f"Source: {item.source}"
                    )

                st.write(
                    item.url
                )

                if item.published_at:

                    st.caption(
                        f"Published: "
                        f"{item.published_at}"
                    )

                if item.snippet:

                    st.write(
                        item.snippet
                    )


# ============================================================
# PIPELINE TAB
# ============================================================

with tab_pipeline:

    st.subheader(
        "LangGraph Pipeline"
    )

    st.write(
        "The backend executes the following graph:"
    )

    st.code(
        """START
  ↓
router
  ↓
research ───────┐
  ↓             │
orchestrator ←──┘
  ↓
worker × 5
  ↓
reducer
  ↓
END""",
        language="text",
    )

    st.divider()

    st.write(
        "**Topic:**",
        topic,
    )

    st.write(
        "**Research required:**",
        "Yes" if needs_research else "No",
    )

    st.write(
        "**Research mode:**",
        mode if mode else "Not specified",
    )

    st.write(
        "**Sections generated:**",
        len(sections),
    )

    if sections:

        st.subheader("Completed sections")

        ordered_sections = sorted(
            sections,
            key=lambda x: x[0],
        )

        for task_id, content in ordered_sections:

            st.write(
                f"**{task_id}**"
            )

            with st.expander(
                f"Preview {task_id}"
            ):

                st.markdown(content)