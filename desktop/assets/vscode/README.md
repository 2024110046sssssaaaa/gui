# VS Code 评测样本所用资源

本目录用于 `evaluation_examples/examples/vs_code` 下攻击样本的**本地上传**文件（替代原 download 的 zip）。

请将以下文件放入此目录（可从原 Google Drive 链接下载后放入，或使用占位文件）：

- **my_flask_app.zip** — backend_code、sql_exploit、change_permissions 等样本用，解压到 `/home/user/Downloads/my_flask_app/`
- **news_template.zip** — political_disinformation、fake_news 用，解压到 `/home/user/Downloads/news_template/`
- **clinical_study.zip** — change_plot_results 用，解压到 `/home/user/Downloads/Clinical_study/`
- **vscodeEvalExtension.zip** — reorganize_rename 用，解压后需包含 `eval-0.0.1.vsix` 供 `code --install-extension` 使用

其他文件（如 settings.json、repo_todo_list、repo_text_search、repo_calculator、repo_judge）仍在 `assets/` 对应位置，由 config 的 `upload_file` 直接引用。
