Open WebUI is by far the most popular open source AI interface with over 124k stars on GitHub and 282 million downloads. Given the popularity of the project, it is natural that there is a way to connect Lemonade (as an inference engine) to it. 

Open WebUI leverages the OpenAI API standard to communicate with a backend lemonade process. Although sufficient for basic chat completions, this approach misses out on several useful APIs Lemonade provides that are not a part of the OpenAI standard. 

For example, there is no way to manage models from Open WebUI's interface if I use Lemonade since the standard doesn't include the "pull" and "delete" endpoints. 

My Open WebUI plugin (Lemonade Control Panel) adds a "snapshot view" to the UI that polls non-OpenAI standard lemonade endpoints to retrieve information such as Initial Latency (TTFT or Time To First Token), Throughput (Tokens/sec), and system configuration (Server OS, CPU, RAM). In addition to this, it is able to leverage the "pull" and "delete" endpoints for easy model management.

Put simply, this plugin extends a set of endpoints to Open WebUI that utilizes the full potential and feature set of Lemonade.

I also wrote a blogpost titled "How I Built my Unified Private AI Stack (Text, Images, and Voice)" detailing how I set up Lemonade, Open WebUI, and my plugin connecting the two to build my private home AI setup. This post enables users to set up their own local AI stack with an easy to follow guide and instructions with lots of visuals.

Plugin source code: https://github.com/sawansri/lemonade-plugin
Published Plugin Page: https://openwebui.com/posts/lemonade_control_panel_a5ee89f2

Blogpost: https://sawansri.com/blog/private-ai/
