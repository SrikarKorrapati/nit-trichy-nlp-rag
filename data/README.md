# Local corpus

Downloaded and extracted data stays local and is ignored by Git. Run `python3 scripts/use_demo_data.py` for the included two-course example.

The application reads:

- `nit_trichy_chunks.jsonl`: website chunks with `chunk_id`, `text`, `source_url`, and `title`.
- `nit_trichy_cp_course_details.json`: a JSON array of course records; see `examples/nit_trichy_cp_course_details.json` for the schema.
- `nit_trichy_cp_course_detail_chunks.jsonl`: optional course chunks when the detailed JSON is absent.

After adding data, restart the application. Check extraction quality, source dates, and student-record exclusions before using a larger corpus. The later comprehensive crawl is separate and has not been indexed into this application.
