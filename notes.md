## MongoDB Project — Working Notes

### Goal

Create a **demo project** that uses:

* **Pulumi Neo** (MCP workflow) to provision infrastructure.
* **MongoDB** as a managed resource.
* A **Python app** running inside a Docker container.

This demo should effectively extend the **Python workshop** example by adding a **MongoDB layer** and demonstrating **Pulumi + Neo + MCP orchestration**.

---

### Plan / Workflow

1. **Environment Setup**

   * Obtain necessary **cloud credentials** (AWS or MongoDB Atlas, depending on setup).
   * Ensure Neo (or Pulumi) can access these credentials correctly.

2. **Infrastructure via Neo**

   * Use Neo to:

     * Set up MongoDB (Atlas cluster or local container).
     * Deploy a Docker container running the Python project.
   * Target outcome: fully automated environment provisioning.

3. **Fallback / Alternate Flow**

   * If an **Anthropic guest** prefers using **Claude Cloud Code**, ensure compatibility:

     * Either switch from Neo to Cloud Code.
     * Or use Neo for base infra + Cloud Code for app logic.

4. **Testing & Validation**

   * Verify that Neo can:

     * Detect the stack from the repo.
     * Run `pulumi preview` successfully.
     * Provision both the container and Mongo.
   * Use `README` hints to guide Neo if autodetection fails.

---

### Current Issues

* **Neo preview failing** — cannot currently run `pulumi preview` on the project.
* May need to:

  * Manually set the stack in the repo.
  * Add configuration hints (e.g., in `Pulumi.yaml`, or via README prompts).
  * Validate Neo environment variables and stack references.

---

### Next Steps

1. Get Neo running a basic **preview** successfully.
2. Add Mongo provisioning instructions.
3. Integrate the Docker container setup.
4. Record and validate the full demo flow.
5. Prepare backup plan using **Cloud Code** if Anthropic collaboration dictates.
