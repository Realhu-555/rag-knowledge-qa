"""Gradio前端"""
import gradio as gr
from src.core.rag_engine import RAGEngine


def create_demo():
    """创建Gradio界面"""
    engine = RAGEngine()

    def answer_question(question: str) -> tuple[str, str, str]:
        """处理用户问题"""
        if not question.strip():
            return "", "", ""

        response = engine.query(question)

        # 格式化回答
        answer = response.answer

        # 格式化引用来源
        sources_text = "📚 参考来源：\n"
        for i, source in enumerate(response.sources, 1):
            file_name = source["metadata"].get("source", "未知")
            section = source["metadata"].get("section", "")
            score = source["score"] * 100
            sources_text += f"[{i}] {file_name} - {section} (相关度: {score:.1f}%)\n"

        # 格式化统计信息
        timing = response.timing
        usage = response.usage
        stats_text = (
            f"⏱ 检索 {timing['retrieval_ms']:.0f}ms | "
            f"生成 {timing['generation_ms']:.0f}ms | "
            f"Token {usage['total_tokens']}"
        )

        return answer, sources_text, stats_text

    # 创建界面
    with gr.Blocks(title="RAG智能问答助手", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🧠 RAG 智能问答助手")

        with gr.Row():
            with gr.Column(scale=2):
                question_input = gr.Textbox(
                    label="💬 输入你的问题",
                    placeholder="例如：什么是RAG？",
                    lines=2
                )
                submit_btn = gr.Button("发送", variant="primary")

                answer_output = gr.Textbox(label="🤖 回答", lines=8)
                stats_output = gr.Textbox(label="📊 统计信息", lines=1)

            with gr.Column(scale=1):
                sources_output = gr.Textbox(label="📚 参考来源", lines=15)

        # 绑定事件
        submit_btn.click(
            fn=answer_question,
            inputs=[question_input],
            outputs=[answer_output, sources_output, stats_output]
        )

        question_input.submit(
            fn=answer_question,
            inputs=[question_input],
            outputs=[answer_output, sources_output, stats_output]
        )

    return demo


if __name__ == "__main__":
    demo = create_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860)
