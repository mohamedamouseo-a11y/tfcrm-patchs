# TFCRM Egypt Location + Walk-in Patch V2

نسخة V2 المصححة بعد اكتشاف أن ZIP الخاص بـ V1 كان غير صالح للاستخراج.

## طريقة التطبيق
1. استخدم ملفات هذا الفولدر فقط ولا تستخدم V1.
2. شغّل `python3 ASSEMBLE_PATCHER.py` لإعادة إنشاء `apply_tfcrm_egypt_walkin_patch.py` من الأجزاء النصية.
3. الـAssembler يتحقق من SHA256 قبل إنشاء السكربت.
4. نفّذ Dry Run ثم Apply حسب `PROMPT_REPLIT.txt`.

Expected patcher SHA256:
`413a3087eeb29173bdcc1615aa3af5ea15ffbab65acb8915ac2a0e565adf08df`

Base reviewed TFCRM commit:
`0b77201204fcaa79ccbd43798a7b7678ae2c5a4b`