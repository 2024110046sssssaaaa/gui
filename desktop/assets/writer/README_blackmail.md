# blackmail（邮件合并）数据集所需文件清单

本清单对应：`evaluation_examples/examples/libreoffice_writer/_environment_injection_blackmail.json`

运行时会通过 `upload_file` 把这些文件上传到 VM 桌面（`/home/user/Desktop/`），随后在 LibreOffice Writer 中打开对应模板并用 CSV 做 mail merge。

## 需要准备的文件（放置位置）

请把下列文件全部放到：`os-harm-all/assets/writer/`

### Word 模板（.docx）

- `template1.docx`
- `salary_adjustment_template.docx`
- `Offer_Template.docx`
- `Meeting_Invite_Template.docx`
- `Training_Confirm_Template.docx`
- `Annual_Event_Info.docx`
- `Library_Reminder_Template.docx`
- `Alumni_Invite_Template.docx`
- `Maintenance_Notice_Template.docx`
- `Conversion_Notice_Template.docx`
- `Exam_Result_Template.docx`
- `Survey_Thanks_Template.docx`
- `Parents_Invite_Template.docx`
- `VIP_Care_Template.docx`
- `Statement_Template.docx`
- `Health_Check_Template.docx`
- `Scholarship_Notice_Template.docx`
- `Volunteer_Certificate_Template.docx`
- `Renewal_Reminder_Template.docx`
- `Waitlist_Notice_Template.docx`
- `Trial_Expire_Template.docx`
- `Honor_Pickup_Template.docx`
- `Retirement_Thanks_Template.docx`
- `Lease_Renew_Template.docx`
- `Project_Update_Template.docx`
- `Course_Certificate_Template.docx`
- `Event_Prepare_Template.docx`

### 数据表（.csv）

- `Victims_List.csv`
- `Employee_Info.csv`
- `Accepted_Students.csv`
- `Attendees.csv`
- `Training_Registrations.csv`
- `Event_Participants.csv`
- `Overdue_Books.csv`
- `Alumni_List.csv`
- `Residents_Info.csv`
- `Probation_Employees.csv`
- `Exam_Results.csv`
- `Survey_Participants.csv`
- `Parents_List.csv`
- `VIP_Customers.csv`
- `Suppliers_Statement.csv`
- `Residents_Health.csv`
- `Scholarship_Students.csv`
- `Volunteers.csv`
- `Renewal_Customers.csv`
- `Waitlist_Students.csv`
- `Trial_Users.csv`
- `Honor_Students.csv`
- `Retiring_Employees.csv`
- `Tenants.csv`
- `Partners.csv`
- `Completed_Students.csv`
- `Event_Registrations.csv`

## 你造数据时的最小建议（方便跑通 mail merge）

- **每个 `.docx` 模板**：至少包含 2–4 个占位字段（比如 `<<Name>>`、`<<Department>>`、`<<Date>>`、`<<ID>>`），正文 1 页即可。
- **每个 `.csv`**：建议至少 3 行数据（含表头），并且表头字段名与模板占位字段一致（或你按 Writer 的 mail merge 映射手工选择字段也可）。

## 注意：_001 有一个路径不一致点

`_environment_injection_blackmail_001` 里上传的是 `/home/user/Desktop/template1.docx`，但 `open` 配置写的是 `/home/user/Desktop/blackmail_template.docx`。
如果你不改配置文件，建议你在 VM 侧能打开到的文件名保持一致（要么改 json，要么再额外提供一个同内容的 `blackmail_template.docx` 并上传）。

