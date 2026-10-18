# McGurk demo: post copy

The titles don't name either word, so nobody is primed before the first listen.

## YouTube (wide: `renders/promo/final/mcgurk-youtube.mp4`)

**Published 2026-10-17:** https://youtu.be/-VAw_z6oKpQ, titled "The McGurk effect: what you see changes what you hear",
with frame 0 (`renders/promo/final/mcgurk-youtube-thumbnail.jpg`) as the thumbnail.

**Drafted title:** Same audio, different word: the McGurk effect in AI lip sync

**Description:**

> Both shots play the exact same audio. Only the lips change, yet most people hear "Prompt" in one and "Pront" in the
> other.
>
> That's the McGurk effect: what you see changes what you hear. If a generated mouth never closes for P, B or M, viewers
> hear a different word, even over perfect audio. When you lip-sync AI video, check the closures, not just the timing.
>
> The shot is from an AI-generated parody: the face, voice and scene are all synthetic.
>
> #McGurkEffect #AIVideo #LipSync

**Tags:** McGurk effect, lip sync, AI lip sync, AI video, generative AI, speech perception, audiovisual illusion

**Settings:** not made for kids; altered or synthetic content: yes (a realistic likeness of a real person); category
Science & Technology.

## Site project (draft)

Notion Projects entry "The McGurk Effect" (Public and Featured off, not published):
https://app.notion.com/p/3fcedb27f12481b48653c0deaaaf9f30. It embeds the X cut from R2,
https://assets.cultural-alignment.com/mcgurk-effect/7aa6d93c904320716d4a1af2e3137ac53b38af8d4a86254001447eb8ae701f9f.mp4
(`renders/promo/final/mcgurk-x.mp4`, content-addressed by its SHA-256).

## Shorts, Reels, TikTok (vertical: `renders/promo/final/mcgurk-vertical.mp4`)

**Published 2026-10-17**, all three with `renders/promo/final/mcgurk-vertical-thumbnail.jpg` (frame 0) as the cover:

- YouTube Shorts: https://youtube.com/shorts/XiuEb4TusCA
- TikTok: https://www.tiktok.com/@transitive.bs/video/7697618229010746637
- Instagram Reel: https://www.instagram.com/p/DemJfUphw-J/

**Shorts title:** Same audio, different word? The McGurk effect in AI lip sync

**Caption:**

> Same audio. Only the lips change. What did you hear?
>
> That's the McGurk effect: what you see changes what you hear. If you lip-sync AI video, make sure the mouth closes on
> P, B and M.
>
> #McGurkEffect #AIVideo #LipSync #GenerativeAI

**AI labels:** Shorts: altered or synthetic content, yes. Instagram: turn on the AI label. TikTok: turn on
"AI-generated content".

## Community shares (2026-10-18)

Drafted in Chrome, reviewed by the author, then posted:

- Hacker News (McGurk write-up): https://news.ycombinator.com/item?id=50138671, titled "The McGurk effect: what you see changes what you hear"
- Latent Space Discord, #share-your-work (the Creed): https://discord.com/channels/822583790773862470/1209672547642249216/1561275837112655883
- Latent Space Discord, #genmedia-creative-ai-video-… (McGurk PSA): https://discord.com/channels/822583790773862470/1397010677364953149/1561275935288729741
- ElevenLabs Discord, #showcase forum (the Creed; tags ElevenMusic, Video): https://discord.com/channels/1066739690436313158/1561275590386917407

## Reddit drafts (2026-10-18, to paste by hand: Claude in Chrome blocks reddit.com)

Rules come from third-party rule indexes (read Sep 24 to Oct 12); hidden karma or account-age gates aren't visible there. Space the three posts out over a few days.

### r/ClaudeAI (flair: "Built with Claude", if offered)

**Posted 2026-10-18** by the author.

**Title:** I made a Full Metal Jacket parody of AI engineers, with Claude Code running the whole video pipeline

**Body:**

```markdown
**Video (76 s):** https://www.youtube.com/watch?v=GT9zYmPhSys

It's the barracks creed scene from *Full Metal Jacket*, recast for AI engineering: AI engineers on X are the recruits swearing allegiance to their software factories, and Jensen Huang is the drill instructor.

**How Claude helped: pretty much everything except the approvals.**

- **Script:** rewrote every line to land on the original's beats (within two syllables of each line), and built review pages where I left notes per line and pasted them back.
- **Voices:** cut one sung Eleven Music take into the recruits' chant, cloned Jensen's voice in Fish Audio from ~10 minutes of clean interview audio, and placed every read on the timeline without ever stretching the audio.
- **Shots:** wrote the keyframe prompts, ran Nano Banana Pro and MiniMax H3 Max on fal, and redid the lip sync wherever a mouth didn't sell its line. 117 generations, about $97, logged with costs.
- **Captions, title card and credits:** force-aligned every caption word to the vocals and rendered it all locally in HyperFrames.

**My favorite moment:** Jensen's "PROMPT!" kept sounding like "PRONT!" and I was sure the audio was broken. Claude checked, pushed back that the audio was identical to the take I'd approved, and figured out it was the McGurk effect: the generated mouth never closed for the M and P. A new lip sync over the same audio fixed it.

How it was made: https://www.transitivebullsh.it/projects/the-ai-engineers-creed-full-metal-jacket-parody
Source: https://github.com/transitive-bullshit/my-software-factory

The faces and voices are synthetic portrayals of real people, in affectionate parody.
```

### r/ClaudeCode (flair: showcase, if offered)

**Not posted yet:** waiting a while after the r/ClaudeAI post (author's call).

**Title:** How Claude Code made a 76-second AI video end to end: review pages, cost-logged generations, measured captions

**Body:**

```markdown
I made a Full Metal Jacket parody of AI engineers (https://www.youtube.com/watch?v=GT9zYmPhSys) with Claude Code (Opus 5.5) driving the whole pipeline. A few patterns that made it work:

- **One master timeline.** `data/script.json` holds every shot and line with the original timing. Claude wrote a Python script per stage (prep, voices, shots, assembly, captions, release) that reads from it.
- **A review loop instead of chat.** Claude generates HTML review pages with the original moment, the new line and a feedback box per line, plus a "copy all notes" button. I paste the notes back, it updates the script and rebuilds.
- **Spend gated on approval.** Every fal call is cached by output and logged with its estimated cost, so re-runs are free. Keyframes and character sheets get approved before anything is animated. Total: 117 generations, about $97.
- **Rules in AGENTS.md that saved hours:** never re-time generated audio (regenerate instead), run MLX and torch in separate processes (together they can deadlock), and never commit the film's dialogue.
- **Measure, don't eyeball.** Caption timing is force-aligned to the vocals and checked against the separated vocals of the finished mix (line starts within 25 ms), and an audit step checks every shot against its source clip.
- **Bugs it diagnosed:** a lip sync that made "PROMPT!" read as "PRONT!" (the McGurk effect); H3 rendering frames ~2.5% wider than its keyframe (fixed with exact 16:9 keyframes); camera push-ins on every shot (fixed by anchoring each shot's last frame); and a cache keyed by file name that kept serving an old take.

Stack: Claude Code, fal (Nano Banana Pro, MiniMax H3 Max, Sync-3), Eleven Music, Fish Audio, HyperFrames, ffmpeg, uv.

Write-up: https://www.transitivebullsh.it/projects/the-ai-engineers-creed-full-metal-jacket-parody
Source (the whole working directory, AGENTS.md included): https://github.com/transitive-bullshit/my-software-factory
```

### r/aivideo (upload the video file; links only in a comment)

**Posted 2026-10-18** by the author.

**Title:** The AI Engineer's Creed, a Full Metal Jacket AI parody

**Video file:** `renders/final/ai-engineers-creed-youtube.mp4` (87 MB, 1080p)

**First comment:**

```markdown
A parody of the barracks creed scene from Full Metal Jacket: AI engineers from X are the recruits, swearing allegiance to their software factories, and Jensen Huang is the drill instructor. The faces and voices are synthetic portrayals of real people, in affectionate parody.

Made with Claude Code (Opus 5.5) running the pipeline: Nano Banana Pro keyframes, MiniMax H3 Max animation, Sync-3 and H3 Max lip sync, one Eleven Music take for the whole chant, a Fish Audio voice clone for Jensen, and HyperFrames for the captions and credits. 117 generations, about $97.

YouTube: https://www.youtube.com/watch?v=GT9zYmPhSys
How it was made: https://www.transitivebullsh.it/projects/the-ai-engineers-creed-full-metal-jacket-parody
```

## McGurk drafts (2026-10-18): Reddit to paste by hand, Discord after joining

Each Reddit link opens that subreddit's submit form with the title and the YouTube link filled in. Pick the flair, post, then add the comment right away. Rules come from third-party rule indexes, some from early 2025; hidden karma or account-age gates aren't visible there. Space the posts over a few days.

### r/cogsci

**Posted 2026-10-18** by the author.

[Open the prefilled r/cogsci submit form](https://www.reddit.com/r/cogsci/submit?type=LINK&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D-VAw_z6oKpQ&title=Same%20audio%2C%20two%20AI%20lip%20syncs%3A%20when%20the%20mouth%20never%20closes%2C%20%2Fm%2F%20is%20heard%20as%20%2Fn%2F%20%28McGurk%20effect%29)

**Title:** Same audio, two AI lip syncs: when the mouth never closes, /m/ is heard as /n/ (McGurk effect)

**Link:** https://www.youtube.com/watch?v=-VAw_z6oKpQ

**First comment:**

```markdown
I hit this by accident while making an AI-generated video. The audio in both clips is identical; only the lip sync differs. In one, the generated mouth never closes for the M and P of "prompt", and the word reads as "pront": with the lip closure missing from the visual signal, the percept shifts to an alveolar /n/, the same kind of fusion as the classic auditory /ba/ plus visual /ga/ heard as /da/.

The original paper: McGurk, H. & MacDonald, J. (1976). Hearing lips and seeing voices. *Nature*, 264, 746–748. https://doi.org/10.1038/264746a0

A review of the 40 years since: Alsius, A., Paré, M. & Munhall, K. G. (2018). Forty years after "Hearing lips and seeing voices": the McGurk effect revisited. *Multisensory Research*, 31(1–2), 111–144. https://doi.org/10.1163/22134808-00002565

Curious whether people here hear it on the first listen, and whether it survives once you know what to look for.
```

### r/generativeAI

**Posted 2026-10-18** by the author.

[Open the prefilled r/generativeAI submit form](https://www.reddit.com/r/generativeAI/submit?type=LINK&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D-VAw_z6oKpQ&title=AI%20lip%20sync%20tip%3A%20if%20the%20mouth%20never%20closes%20on%20P%2C%20B%20or%20M%2C%20viewers%20hear%20a%20different%20word%20%28the%20McGurk%20effect%29)

**Title:** AI lip sync tip: if the mouth never closes on P, B or M, viewers hear a different word (the McGurk effect)

**Link:** https://www.youtube.com/watch?v=-VAw_z6oKpQ

**Flair:** Video Art, or the closest video flair

**First comment:**

```markdown
Found this the hard way: in a generated shot, Jensen's "PROMPT!" kept sounding like "PRONT!" even though the audio was identical to the take I'd approved. The generated mouth never closed for the M and P, and the brain trusts the lips. A second lip sync pass over the same audio, with proper closures, fixed it.

So when you QA lip sync, scrub to every P, B and M and check that the lips actually close. Timing alone isn't enough.

It came up while making a longer parody (Nano Banana Pro, MiniMax H3 Max, Sync-3 and Fish Audio, with Claude Code running the pipeline). Write-up: https://www.transitivebullsh.it/projects/the-mcgurk-effect
```

### r/psychology

**Posted 2026-10-18** by the author.

[Open the prefilled r/psychology submit form](https://www.reddit.com/r/psychology/submit?type=LINK&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D-VAw_z6oKpQ&title=The%20McGurk%20effect%2C%20demonstrated%20with%20AI%20lip%20sync%3A%20identical%20audio%2C%20but%20the%20lips%20change%20the%20word%20you%20hear)

**Title:** The McGurk effect, demonstrated with AI lip sync: identical audio, but the lips change the word you hear

**Link:** https://www.youtube.com/watch?v=-VAw_z6oKpQ

**First comment:**

```markdown
The research behind it: McGurk, H. & MacDonald, J. (1976). Hearing lips and seeing voices. *Nature*, 264, 746–748. https://doi.org/10.1038/264746a0

Review: Alsius, A., Paré, M. & Munhall, K. G. (2018). Forty years after "Hearing lips and seeing voices": the McGurk effect revisited. *Multisensory Research*, 31(1–2), 111–144. https://doi.org/10.1163/22134808-00002565

Both clips share the exact same audio track; only the lip sync differs. It turned up in an AI-generated video, where a lip sync that never closed for the M and P made "prompt" sound like "pront".
```

### r/ScienceTeachers

**On hold** (author's call, 2026-10-18).

[Open the prefilled r/ScienceTeachers submit form](https://www.reddit.com/r/ScienceTeachers/submit?type=LINK&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D-VAw_z6oKpQ&title=A%2050-second%20McGurk%20effect%20demo%20for%20perception%20lessons%3A%20same%20audio%2C%20two%20lip%20syncs)

**Title:** A 50-second McGurk effect demo for perception lessons: same audio, two lip syncs

**Link:** https://www.youtube.com/watch?v=-VAw_z6oKpQ

**First comment:**

```markdown
Why it might be useful in class: it's a quick, concrete demo of multisensory integration. Both clips use the identical audio track and only the mouth movements differ, so students can test it themselves: listen with eyes closed (the same word twice), then watch (many hear two different words). It also opens a good discussion about AI-generated video, since the effect turned up by accident in an AI lip sync.

The original study, if you want to pair it with a reading: McGurk, H. & MacDonald, J. (1976). Hearing lips and seeing voices. *Nature*, 264, 746–748. https://doi.org/10.1038/264746a0
```

### Sync (sync. labs) Discord

**Posted 2026-10-18** by the author.

[Join or open the Sync (sync. labs) Discord](https://discord.gg/synclabs), then post in the showcase or share-your-work channel (visible once you've joined).

```text
lip sync QA tip, learned the hard way 🤯

in an AI-generated shot, the mouth never closed for the M and P of "PROMPT!", so it sounded like "PRONT!" even though the audio was identical to the approved take. that's the McGurk effect: when sight and sound disagree, the lips win.

a Sync-3 pass over the same audio, with proper closures, fixed it. so when you QA lip sync, check that every P, B and M actually closes, not just the timing.

same audio, two lip syncs: https://youtu.be/-VAw_z6oKpQ
write-up: <https://www.transitivebullsh.it/projects/the-mcgurk-effect>
```

### fal Discord

**Posted 2026-10-18** by the author.

[Join or open the fal Discord](https://discord.gg/fal-ai), then post in the showcase channel (visible once you've joined).

```text
PSA for anyone doing lip sync: the McGurk effect is real 🤯

in a generated shot, Jensen's "PROMPT!" kept sounding like "PRONT!" even though the audio was identical to the approved take, because the mouth never closed for the M and P. the whole pipeline ran on fal (Nano Banana Pro, MiniMax H3 Max, Sync-3), and a second lip sync pass over the same audio fixed it.

QA tip: check that the lips close on every P, B and M, not just the timing.

same audio, two lip syncs: https://youtu.be/-VAw_z6oKpQ
write-up: <https://www.transitivebullsh.it/projects/the-mcgurk-effect>
```

Hedra's Discord was left out: its showcase is for work made with Hedra, and this wasn't.
