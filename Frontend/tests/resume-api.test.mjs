import assert from "node:assert/strict";
import test from "node:test";
import { deleteResume, downloadResume, getCandidateProfile, getResumeAnalysis, listResumes, uploadResume } from "../lib/api-client.ts";
import { MAX_RESUME_BYTES, validateResumeFile } from "../components/profile/resume-upload-service.ts";

const record = {
  id: 12,
  user_id: 7,
  original_name: "resume.pdf",
  stored_name: "12_resume.pdf",
  uploaded_at: "2026-01-02T03:04:05Z",
  download_url: "/resume/12/download",
};

const analysis = {
  resume_id: 12,
  original_name: "resume.pdf",
  status: "completed",
  pipeline_version: "1.0.0",
  extraction_status: "success",
  page_count: 2,
  sections: { skills: "Python and SQL" },
  detected_section_names: ["skills"],
  extracted_skills: [{
    skill: "Python",
    source_sections: ["skills"],
    occurrences: [{ section: "skills", text: "Python", start: 0, end: 6 }],
  }],
  skill_count: 1,
  skill_extraction_method: "knowledge_graph_keyword_matching",
};

const candidateProfile = {
  id: 4,
  user_id: 7,
  resume_id: 12,
  skills: [{
    skill: "Python",
    source_sections: ["skills"],
    occurrences: [{ section: "skills", text: "Python and SQL", start: 0, end: 6 }],
  }],
  education: ["BSc Computer Science"],
  experience: ["Software Developer at Example Co."],
  projects: ["Road2Hire integration"],
  certifications: ["Cloud Fundamentals"],
  updated_at: "2026-01-02T03:04:05Z",
};

test("candidate profile request uses the authenticated backend contract", async () => {
  let request;
  const result = await getCandidateProfile("profile-token", async (url, options) => {
    request = { url, options };
    return Response.json(candidateProfile);
  });

  assert.match(request.url, /\/profile\/candidate$/);
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Authorization, "Bearer profile-token");
  assert.deepEqual(result, candidateProfile);
});

test("candidate profile rejects missing authentication, API errors, and malformed extracted evidence", async () => {
  await assert.rejects(getCandidateProfile(" ", async () => {
    throw new Error("fetch must not be called");
  }), /Sign in to view your candidate profile/);

  await assert.rejects(getCandidateProfile("profile-token", async () =>
    Response.json({ detail: "Candidate profile not found" }, { status: 404 })), (error) => {
    assert.equal(error.status, 404);
    assert.equal(error.message, "Candidate profile not found");
    return true;
  });

  await assert.rejects(getCandidateProfile("profile-token", async () =>
    Response.json({ ...candidateProfile, skills: [{ ...candidateProfile.skills[0], occurrences: [{ section: "skills", text: "Python", start: -1, end: 6 }] }] })),
  /invalid candidate profile response/);
});

test("upload sends required multipart fields and bearer authorization without setting multipart content type", async () => {
  let request;
  const file = new File(["%PDF-1.7"], "resume.pdf", { type: "application/pdf" });
  const result = await uploadResume(file, 7, "test-token", async (url, options) => {
    request = { url, options };
    return Response.json({ message: "Resume uploaded successfully", resume: { ...record, file_path: "private/storage/path.pdf" } });
  });

  assert.match(request.url, /\/resume\/upload$/);
  assert.equal(request.options.method, "POST");
  assert.equal(request.options.headers.Authorization, "Bearer test-token");
  assert.equal("Content-Type" in request.options.headers, false);
  assert.equal(request.options.body.get("user_id"), "7");
  assert.equal(request.options.body.get("file").name, "resume.pdf");
  assert.equal(result.message, "Resume uploaded successfully");
  assert.equal(result.resume.id, 12);
});

test("resume listing sends bearer authorization and validates actual list fields", async () => {
  let request;
  const result = await listResumes("test-token", async (url, options) => {
    request = { url, options };
    return Response.json([record]);
  });

  assert.match(request.url, /\/resumes$/);
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Authorization, "Bearer test-token");
  assert.deepEqual(result, [record]);
});

test("upload and list surface FastAPI errors and network failures safely", async () => {
  const file = new File(["%PDF-1.7"], "resume.pdf", { type: "application/pdf" });
  await assert.rejects(uploadResume(file, 7, "secret-token", async () =>
    Response.json({ detail: "User not found" }, { status: 404 })), (error) => {
    assert.equal(error.status, 404);
    assert.equal(error.message, "User not found");
    assert.equal(error.message.includes("secret-token"), false);
    return true;
  });
  await assert.rejects(listResumes("test-token", async () => { throw new Error("offline"); }), /Could not connect to the Road2Hire API/);
});

test("malformed resume payloads are rejected", async () => {
  await assert.rejects(listResumes("test-token", async () => Response.json([{ id: 1 }])), /invalid resume list/);
  const file = new File(["%PDF-1.7"], "resume.pdf", { type: "application/pdf" });
  await assert.rejects(uploadResume(file, 7, "test-token", async () =>
    Response.json({ message: "ok", resume: { id: 1 } })), /invalid resume upload response/);
});

test("analysis retrieval sends resume id and bearer token and validates the backend payload", async () => {
  let request;
  const result = await getResumeAnalysis(12, "analysis-token", async (url, options) => {
    request = { url, options };
    return Response.json(analysis);
  });

  assert.match(request.url, /\/resume\/12\/analysis$/);
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Authorization, "Bearer analysis-token");
  assert.deepEqual(result, analysis);
});

test("analysis accepts completed empty results distinctly from an unrequested analysis", async () => {
  const emptyAnalysis = {
    ...analysis,
    sections: {},
    detected_section_names: [],
    extracted_skills: [],
    skill_count: 0,
  };
  assert.deepEqual(await getResumeAnalysis(12, "analysis-token", async () => Response.json(emptyAnalysis)), emptyAnalysis);
});

test("analysis retrieval rejects missing authentication, API failures, and malformed shapes", async () => {
  await assert.rejects(getResumeAnalysis(12, "  ", async () => {
    throw new Error("fetch must not be called");
  }), /Sign in to view resume analysis/);
  await assert.rejects(getResumeAnalysis(12, "analysis-token", async () =>
    Response.json({ detail: "Resume not found" }, { status: 404 })), (error) => {
    assert.equal(error.status, 404);
    assert.equal(error.message, "Resume not found");
    return true;
  });
  await assert.rejects(getResumeAnalysis(12, "analysis-token", async () => Response.json({
    ...analysis,
    extracted_skills: [{ skill: "Python", source_sections: ["skills"], occurrences: [{ section: "skills", text: "Python", start: -1, end: 6 }] }],
  })), /invalid resume analysis response/);
  await assert.rejects(getResumeAnalysis(12, "analysis-token", async () => Response.json({ ...analysis, resume_id: 13 })), /invalid resume analysis response/);
});

test("PDF validation matches backend extension and 5 MiB size limit", () => {
  assert.equal(MAX_RESUME_BYTES, 5 * 1024 * 1024);
  assert.equal(validateResumeFile({ name: "candidate.PDF", size: MAX_RESUME_BYTES }), null);
  assert.match(validateResumeFile({ name: "candidate.docx", size: 100 }), /PDF file/);
  assert.match(validateResumeFile({ name: "candidate.pdf", size: MAX_RESUME_BYTES + 1 }), /5 MiB/);
});

test("resume download sends bearer authorization and returns the PDF blob", async () => {
  let request;
  const pdf = new Blob(["%PDF-1.7 test"], { type: "application/pdf" });

  const result = await downloadResume(12, "download-token", async (url, options) => {
    request = { url, options };
    return new Response(pdf, {
      status: 200,
      headers: { "Content-Type": "application/pdf" },
    });
  });

  assert.match(request.url, /\/resume\/12\/download$/);
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Accept, "application/pdf");
  assert.equal(request.options.headers.Authorization, "Bearer download-token");
  assert.equal(await result.text(), "%PDF-1.7 test");
});

test("resume download rejects missing authentication, invalid IDs, HTTP errors, and network failures", async () => {
  await assert.rejects(downloadResume(12, " ", async () => {
    throw new Error("fetch must not be called");
  }), /Sign in to download your resume/);

  await assert.rejects(downloadResume(0, "token", async () => {
    throw new Error("fetch must not be called");
  }), /valid resume/);

  await assert.rejects(downloadResume(12, "token", async () =>
    Response.json({ detail: "Resume not found" }, { status: 404 })), (error) => {
    assert.equal(error.status, 404);
    assert.equal(error.message, "Resume not found");
    assert.equal(error.message.includes("token"), false);
    return true;
  });

  await assert.rejects(downloadResume(12, "token", async () => {
    throw new Error("offline");
  }), /Could not connect to the Road2Hire API/);
});

test("resume deletion sends authenticated DELETE and validates the returned resume ID", async () => {
  let request;
  const result = await deleteResume(12, "delete-token", async (url, options) => {
    request = { url, options };
    return Response.json({
      message: "Resume deleted successfully",
      resume_id: 12,
    });
  });

  assert.match(request.url, /\/resumes\/12$/);
  assert.equal(request.options.method, "DELETE");
  assert.equal(request.options.headers.Authorization, "Bearer delete-token");
  assert.deepEqual(result, {
    message: "Resume deleted successfully",
    resume_id: 12,
  });
});

test("resume deletion rejects missing authentication, invalid IDs, API errors, and malformed responses", async () => {
  await assert.rejects(deleteResume(12, " ", async () => {
    throw new Error("fetch must not be called");
  }), /Sign in to delete your resume/);

  await assert.rejects(deleteResume(-1, "token", async () => {
    throw new Error("fetch must not be called");
  }), /valid resume/);

  await assert.rejects(deleteResume(12, "token", async () =>
    Response.json({ detail: "Resume not found" }, { status: 404 })), (error) => {
    assert.equal(error.status, 404);
    assert.equal(error.message, "Resume not found");
    return true;
  });

  await assert.rejects(deleteResume(12, "token", async () =>
    Response.json({ message: "Deleted", resume_id: 13 })), /invalid resume deletion response/);

  await assert.rejects(deleteResume(12, "token", async () =>
    Response.json({ message: "", resume_id: 12 })), /invalid resume deletion response/);
});
