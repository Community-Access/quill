/*
 * QuillVille runtime bootstrap -- self-healing first-run install.
 *
 * When the launcher finds no runtime (neither the shared QuillVille runtime nor
 * a private one beside it), instead of just erroring it can offer to download
 * and install the shared runtime once. Every QuillVille app after that starts
 * instantly. The download shows an accessible progress dialog (a real Win32
 * progress bar, whose value is exposed to screen readers via MSAA, plus a
 * status line and a live percentage in the window title).
 *
 * Windows-only. On other platforms this is a no-op returning nonzero.
 */
#ifndef QL_RUNTIME_BOOTSTRAP_H
#define QL_RUNTIME_BOOTSTRAP_H

/*
 * Offer to download + install the shared QuillVille runtime.
 *
 *   display_name  user-facing product name for the prompts (e.g. "Quill Radio")
 *   runtime_url   HTTPS URL of the QuillVille Runtime installer (a GitHub
 *                 release asset). Redirects are followed.
 *
 * Returns 0 if the runtime was installed and the installer reported success
 * (the caller should then re-resolve the runtime). Returns nonzero if the user
 * declined, the download failed, or the install failed.
 */
int ql_bootstrap_runtime(const char *display_name, const char *runtime_url);

#endif /* QL_RUNTIME_BOOTSTRAP_H */
