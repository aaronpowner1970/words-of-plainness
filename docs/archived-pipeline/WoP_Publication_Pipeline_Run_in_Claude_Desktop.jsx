import { useState, useEffect, useCallback } from "react";

// ─── PIPELINE STAGES ───────────────────────────────────────────────
const STAGES = [
  { id: "import", label: "Import", icon: "📥", desc: "Load mastered WAV from Masterchannel" },
  { id: "rename", label: "Rename", icon: "🏷️", desc: "Apply WoP naming convention" },
  { id: "metadata", label: "Metadata", icon: "📝", desc: "Embed ID3 tags & album art" },
  { id: "archive", label: "Archive", icon: "💾", desc: "Three-tier file management" },
  { id: "qa", label: "QA", icon: "🎧", desc: "Quality assurance listen" },
  { id: "website", label: "Website", icon: "🌐", desc: "Deploy to Eleventy site" },
  { id: "distrokid", label: "DistroKid", icon: "🚀", desc: "Upload for distribution" },
  { id: "publish", label: "Published", icon: "✅", desc: "Live on streaming platforms" },
];

const PREFIXES = [
  { code: "##", label: "Chapter Testimony (01–62+)", example: "04_1_When_God_Becomes_Real" },
  { code: "AN", label: "Anthem / Homepage Hymn", example: "AN_1_Calling_the_Straying_Stranger_Home" },
  { code: "SY", label: "Symphonic / Orchestral", example: "SY_1_Seek_and_You_Will_Find_Choral" },
  { code: "AM", label: "Ambient / Instrumental", example: "AM_1_Veil_Meditation" },
  { code: "SP", label: "Special / Collaboration", example: "SP_1_Ministry_Invitation" },
  { code: "OV", label: "Overture / Interlude", example: "OV_1_Pilgrims_Prelude" },
];

const STYLES = [
  "Sacred_Americana", "Americana_Folk", "Celtic_Ballad", "Bluegrass",
  "Contemplative_Worship", "Soul_Worship", "Celtic_Worship",
  "Classical_Crossover", "Classical_Duet", "Choral_Anthem",
  "Cinematic_Inspirational", "Atmospheric_Folk", "Ethereal_Celtic",
  "Hymn_Arrangement", "Sacred_Harp", "Shape_Note",
  "Indie_Folk", "Folk_Rock", "Acoustic_Worship",
  "Female_Vocal", "Male_Baritone", "Duet", "A_Cappella",
  "Meditation", "Instrumental", "Soundscape",
];

const QA_CHECKS = [
  { id: "headphones", label: "Full listen on headphones — no artifacts, pops, or abrupt edits" },
  { id: "speakers", label: "Full listen on speakers/car — bass clarity, vocal presence" },
  { id: "ab_compare", label: "A/B compare with pre-master — mastering improved, not degraded" },
  { id: "filename", label: "Filename follows naming convention" },
  { id: "id3_tags", label: "ID3 tags fully populated and consistent" },
  { id: "album_art", label: "Album art embedded (3000×3000px)" },
  { id: "three_tier", label: "Three-tier archive copies exist (Archive WAV, Distribution WAV, Web MP3)" },
  { id: "isrc", label: "ISRC spreadsheet updated" },
  { id: "lyrics", label: "Lyrics prepared for streaming platform submission" },
  { id: "theology", label: "Theological accuracy verified — lyrics match ministry voice" },
];

// ─── STYLING ───────────────────────────────────────────────────────
const colors = {
  bg: "#0F0E17",
  surface: "#1A1929",
  surfaceHover: "#232240",
  border: "#2D2B55",
  borderActive: "#7B5EA7",
  purple: "#7B5EA7",
  purpleLight: "#A78BFA",
  purpleDim: "#4C3575",
  gold: "#D4A843",
  goldDim: "#8B6914",
  text: "#FFFFFE",
  textMuted: "#94A1B2",
  textDim: "#5A5B7A",
  green: "#2CB67D",
  greenDim: "#1A6B4A",
  red: "#E53170",
  orange: "#F59E0B",
};

// ─── REUSABLE COMPONENTS (defined outside main component to preserve focus) ──
const Input = ({ label, field, value, onChange, placeholder, type = "text", disabled = false }) => (
  <div style={{ marginBottom: 16 }}>
    <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: colors.textMuted, marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>
      {label}
    </label>
    <input
      type={type}
      value={value}
      onChange={e => onChange(field, e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      style={{
        width: "100%", padding: "10px 14px", background: colors.bg, border: `1px solid ${colors.border}`,
        borderRadius: 8, color: colors.text, fontSize: 14, fontFamily: "'JetBrains Mono', monospace",
        outline: "none", boxSizing: "border-box", minWidth: 0,
        opacity: disabled ? 0.5 : 1,
      }}
    />
  </div>
);

const Select = ({ label, field, value, onChange, options, allowCustom = false }) => (
  <div style={{ marginBottom: 16 }}>
    <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: colors.textMuted, marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>
      {label}
    </label>
    <select
      value={value}
      onChange={e => onChange(field, e.target.value)}
      style={{
        width: "100%", padding: "10px 14px", background: colors.bg, border: `1px solid ${colors.border}`,
        borderRadius: 8, color: colors.text, fontSize: 14, outline: "none", boxSizing: "border-box",
        appearance: "none",
      }}
    >
      <option value="">— Select —</option>
      {options.map(o => (
        <option key={typeof o === "string" ? o : o.value} value={typeof o === "string" ? o : o.value}>
          {typeof o === "string" ? o : o.label}
        </option>
      ))}
      {allowCustom && <option value="custom">Custom...</option>}
    </select>
  </div>
);

const StageButton = ({ label, onClick, disabled = false, variant = "primary" }) => {
  const isPrimary = variant === "primary";
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "12px 28px", borderRadius: 10, border: "none", cursor: disabled ? "not-allowed" : "pointer",
        fontSize: 14, fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase",
        background: disabled ? colors.textDim : isPrimary ? `linear-gradient(135deg, ${colors.purple}, ${colors.purpleLight})` : colors.surfaceHover,
        color: disabled ? colors.bg : colors.text,
        opacity: disabled ? 0.4 : 1,
        transition: "all 0.2s ease",
        boxShadow: disabled ? "none" : isPrimary ? `0 4px 20px ${colors.purpleDim}` : "none",
      }}
    >
      {label}
    </button>
  );
};

// ─── MAIN APP ──────────────────────────────────────────────────────
export default function WoPPipeline() {
  const [currentStage, setCurrentStage] = useState(0);
  const [trackData, setTrackData] = useState({
    sourceFile: "",
    prefixType: "##",
    chapterNum: "",
    versionNum: "01",
    title: "",
    styleDescriptor: "",
    customStyle: "",
    artist: "Words of Plainness",
    albumArtist: "Words of Plainness",
    album: "Words of Plainness: Musical Testimonies",
    year: "2026",
    genre: "Christian / Sacred",
    comment: "A Christ-Centered Ministry — words-of-plainness.vercel.app",
    composer: "Aaron J Powner",
    copyright: "© 2026 Aaron J Powner",
    trackNumber: "",
    isrc: "",
    archiveWav: false,
    distroWav: false,
    webMp3: false,
    qaChecks: {},
    websiteDeployed: false,
    distrokidUploaded: false,
    releaseDate: "",
    notes: "",
  });

  const [completedStages, setCompletedStages] = useState(new Set());
  const [showCatalog, setShowCatalog] = useState(false);
  const [catalog, setCatalog] = useState([]);

  const update = useCallback((field, value) => {
    setTrackData(prev => ({ ...prev, [field]: value }));
  }, []);

  const toggleQA = useCallback((id) => {
    setTrackData(prev => ({
      ...prev,
      qaChecks: { ...prev.qaChecks, [id]: !prev.qaChecks[id] }
    }));
  }, []);

  const getFilename = useCallback(() => {
    const prefix = trackData.prefixType === "##"
      ? trackData.chapterNum.padStart(2, "0")
      : trackData.prefixType;
    const version = trackData.versionNum || "01";
    const title = trackData.title.replace(/\s+/g, "_");
    const style = trackData.styleDescriptor === "custom"
      ? trackData.customStyle.replace(/\s+/g, "_")
      : trackData.styleDescriptor;
    return `${prefix}_${version}_${title}${style ? "_" + style : ""}`;
  }, [trackData]);

  const completeStage = useCallback((stageIdx) => {
    setCompletedStages(prev => new Set([...prev, stageIdx]));
    if (stageIdx < STAGES.length - 1) {
      setCurrentStage(stageIdx + 1);
    }
  }, []);

  const addToCatalog = useCallback(() => {
    const entry = {
      filename: getFilename(),
      title: trackData.title,
      style: trackData.styleDescriptor,
      isrc: trackData.isrc,
      releaseDate: trackData.releaseDate,
      completedAt: new Date().toISOString(),
    };
    setCatalog(prev => [...prev, entry]);
  }, [getFilename, trackData]);

  const resetPipeline = useCallback(() => {
    setCurrentStage(0);
    setCompletedStages(new Set());
    setTrackData(prev => ({
      ...prev,
      sourceFile: "", chapterNum: "", versionNum: "01", title: "",
      styleDescriptor: "", customStyle: "", trackNumber: "", isrc: "",
      archiveWav: false, distroWav: false, webMp3: false,
      qaChecks: {}, websiteDeployed: false, distrokidUploaded: false,
      releaseDate: "", notes: "",
    }));
  }, []);

  const allQaPassed = QA_CHECKS.every(c => trackData.qaChecks[c.id]);

  // ─── STAGE PANELS ──────────────────────────────────────────────
  const renderStage = () => {
    switch (STAGES[currentStage].id) {
      case "import":
        return (
          <div>
            {/* Big start-here banner */}
            <div style={{
              padding: "28px 24px", marginBottom: 24, borderRadius: 14, textAlign: "center",
              background: `linear-gradient(135deg, ${colors.purpleDim}66, ${colors.goldDim}44)`,
              border: `2px dashed ${colors.gold}`,
            }}>
              <div style={{ fontSize: 40, marginBottom: 8 }}>🎵</div>
              <h2 style={{ margin: "0 0 6px", color: colors.gold, fontSize: 22, fontWeight: 800 }}>
                Start Here
              </h2>
              <p style={{ margin: 0, color: colors.textMuted, fontSize: 13, lineHeight: 1.6, maxWidth: 440, marginLeft: "auto", marginRight: "auto" }}>
                This tool guides you through each step from mastered WAV to published release.
                It's a <strong style={{ color: colors.text }}>tracking checklist</strong> — you'll do the actual work in
                Masterchannel, Kid3, Audacity, and DistroKid, then confirm each step here.
              </p>
            </div>

            <h3 style={{ color: colors.gold, margin: "0 0 8px", fontSize: 18 }}>Step 1: Log Your Mastered File</h3>
            <p style={{ color: colors.textMuted, margin: "0 0 20px", lineHeight: 1.6, fontSize: 14 }}>
              Open <strong style={{ color: colors.purpleLight }}>Masterchannel</strong> and download your mastered WAV.
              Type the filename below so you have a record of which export you're processing.
            </p>

            {/* Masterchannel settings reminder */}
            <div style={{
              padding: 14, marginBottom: 20, borderRadius: 10, background: colors.bg,
              border: `1px solid ${colors.border}`, fontSize: 13,
            }}>
              <div style={{ color: colors.textMuted, fontWeight: 700, marginBottom: 10, fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
                Recommended Masterchannel Settings
              </div>
              {[
                { label: "Engine", value: "Standard AI", note: "(not Wez Clarke — pop/R&B bias)" },
                { label: "Genre", value: "Folk", note: "(closest to Americana)" },
                { label: "Loudness", value: "-14 LUFS", note: "(Spotify/Apple standard)" },
                { label: "Output", value: "WAV", note: "(highest resolution available)" },
              ].map((s, i) => (
                <div key={i} style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 6 }}>
                  <span style={{ color: colors.textDim, width: 70, flexShrink: 0, fontSize: 12 }}>{s.label}</span>
                  <span style={{ color: colors.purpleLight, fontWeight: 700, fontSize: 13 }}>{s.value}</span>
                  <span style={{ color: colors.textDim, fontSize: 11 }}>{s.note}</span>
                </div>
              ))}
            </div>

            <Input label="Masterchannel Source Filename" field="sourceFile" value={trackData.sourceFile} onChange={update} placeholder="e.g., mastered_export_20260227.wav" />
            <Input label="Notes (optional)" field="notes" value={trackData.notes} onChange={update} placeholder="Any mastering observations, A/B impressions, settings used..." />
            <div style={{ marginTop: 24, textAlign: "center" }}>
              <StageButton label="Begin Pipeline →" onClick={() => completeStage(0)} disabled={!trackData.sourceFile} />
              {!trackData.sourceFile && (
                <div style={{ marginTop: 10, fontSize: 12, color: colors.textDim }}>
                  ↑ Enter a filename above to enable
                </div>
              )}
            </div>
          </div>
        );

      case "rename":
        return (
          <div>
            <h3 style={{ color: colors.gold, margin: "0 0 8px", fontSize: 18 }}>Apply Naming Convention</h3>
            <p style={{ color: colors.textMuted, margin: "0 0 20px", lineHeight: 1.6, fontSize: 14 }}>
              Build the standardized filename. Choose a track type prefix, version number, title, and style descriptor.
            </p>
            <Select label="Track Type" field="prefixType" value={trackData.prefixType} onChange={update} options={PREFIXES.map(p => ({ value: p.code, label: `${p.code} — ${p.label}` }))} />
            {trackData.prefixType === "##" && (
              <Input label="Chapter Number" field="chapterNum" value={trackData.chapterNum} onChange={update} placeholder="e.g., 04" />
            )}
            <Input label="Version Number" field="versionNum" value={trackData.versionNum} onChange={update} placeholder="01 = primary, 02+ = alternates" />
            <Input label="Song Title" field="title" value={trackData.title} onChange={update} placeholder="e.g., When God Becomes Real" />
            <Select label="Style Descriptor" field="styleDescriptor" value={trackData.styleDescriptor} onChange={update} options={STYLES} allowCustom />
            {trackData.styleDescriptor === "custom" && (
              <Input label="Custom Style" field="customStyle" value={trackData.customStyle} onChange={update} placeholder="e.g., Gospel_Piano" />
            )}

            {/* Preview */}
            <div style={{
              marginTop: 20, padding: 16, background: colors.bg, borderRadius: 10,
              border: `1px solid ${colors.borderActive}`, fontFamily: "'JetBrains Mono', monospace",
            }}>
              <div style={{ fontSize: 11, color: colors.textMuted, marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>
                Generated Filename
              </div>
              <div style={{ fontSize: 15, color: colors.purpleLight, wordBreak: "break-all" }}>
                {getFilename() || "—"}<span style={{ color: colors.textDim }}>.wav / .mp3</span>
              </div>
            </div>

            {/* Prefix reference */}
            <div style={{ marginTop: 16, padding: 12, background: `${colors.purpleDim}22`, borderRadius: 8, fontSize: 12 }}>
              <div style={{ color: colors.textMuted, fontWeight: 700, marginBottom: 8 }}>PREFIX REFERENCE</div>
              {PREFIXES.map(p => (
                <div key={p.code} style={{ color: colors.textMuted, marginBottom: 4 }}>
                  <span style={{ color: colors.gold, fontFamily: "monospace", fontWeight: 700 }}>{p.code}</span> — {p.label}
                </div>
              ))}
            </div>

            <div style={{ marginTop: 24 }}>
              <StageButton label="Proceed to Metadata →" onClick={() => completeStage(1)} disabled={!trackData.title} />
            </div>
          </div>
        );

      case "metadata":
        return (
          <div>
            <h3 style={{ color: colors.gold, margin: "0 0 8px", fontSize: 18 }}>Embed ID3 Metadata</h3>
            <p style={{ color: colors.textMuted, margin: "0 0 20px", lineHeight: 1.6, fontSize: 14 }}>
              Embed these tags using <strong style={{ color: colors.text }}>Kid3</strong> (batch editor) or Audacity before distribution.
              Album art must be 3000×3000px minimum, JPEG or PNG, RGB.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <Input label="Title" field="title" value={trackData.title} onChange={update} placeholder="Song title" />
              <Input label="Artist" field="artist" value={trackData.artist} onChange={update} placeholder="Words of Plainness" />
              <Input label="Album Artist" field="albumArtist" value={trackData.albumArtist} onChange={update} placeholder="Words of Plainness" />
              <Input label="Album" field="album" value={trackData.album} onChange={update} placeholder="Album or EP name" />
              <Input label="Track Number" field="trackNumber" value={trackData.trackNumber} onChange={update} placeholder="Position in release" type="number" />
              <Input label="Year" field="year" value={trackData.year} onChange={update} placeholder="2026" />
              <Input label="Genre" field="genre" value={trackData.genre} onChange={update} placeholder="Christian / Sacred" />
              <Input label="Composer" field="composer" value={trackData.composer} onChange={update} placeholder="Aaron J Powner" />
            </div>
            <Input label="Comment" field="comment" value={trackData.comment} onChange={update} placeholder="Ministry URL or description" />
            <Input label="Copyright" field="copyright" value={trackData.copyright} onChange={update} placeholder="© 2026 Aaron J Powner" />

            <div style={{
              marginTop: 16, padding: 14, background: `${colors.goldDim}22`, borderRadius: 8,
              border: `1px solid ${colors.goldDim}`, fontSize: 13, color: colors.gold, lineHeight: 1.6,
            }}>
              💡 <strong>Kid3 Batch Workflow:</strong> Open Kid3 → File → Open Directory → select all WAVs → fill shared fields (Artist, Album, Year, Genre) → apply to all → then set per-track fields (Title, Track Number) individually.
            </div>

            <div style={{ marginTop: 24 }}>
              <StageButton label="Proceed to Archive →" onClick={() => completeStage(2)} disabled={!trackData.title || !trackData.artist} />
            </div>
          </div>
        );

      case "archive":
        return (
          <div>
            <h3 style={{ color: colors.gold, margin: "0 0 8px", fontSize: 18 }}>Three-Tier File Archive</h3>
            <p style={{ color: colors.textMuted, margin: "0 0 20px", lineHeight: 1.6, fontSize: 14 }}>
              Create all three copies. The distributor should <strong style={{ color: colors.red }}>never</strong> be the only copy.
            </p>

            {[
              { field: "archiveWav", tier: "Archive Master", format: "WAV (highest res from Masterchannel)", location: "WoP-Audio/01-Archive-Masters/", note: "Permanent lossless reference. Never re-encode." },
              { field: "distroWav", tier: "Distribution Master", format: "WAV 16/44.1 or 24/44.1", location: "WoP-Audio/02-Distribution-WAVs/", note: "DistroKid upload ready." },
              { field: "webMp3", tier: "Web Master", format: "MP3 320kbps", location: "WoP-Audio/03-Web-MP3s/ + src/assets/audio/", note: "Encoded from Archive WAV via Audacity." },
            ].map(t => (
              <div
                key={t.field}
                onClick={() => update(t.field, !trackData[t.field])}
                style={{
                  padding: 16, marginBottom: 12, borderRadius: 10, cursor: "pointer",
                  background: trackData[t.field] ? `${colors.greenDim}33` : colors.bg,
                  border: `1px solid ${trackData[t.field] ? colors.green : colors.border}`,
                  transition: "all 0.2s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{
                    width: 24, height: 24, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center",
                    background: trackData[t.field] ? colors.green : "transparent",
                    border: `2px solid ${trackData[t.field] ? colors.green : colors.textDim}`,
                    fontSize: 14, color: colors.text,
                  }}>
                    {trackData[t.field] ? "✓" : ""}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, color: colors.text, fontSize: 14 }}>{t.tier}</div>
                    <div style={{ color: colors.textMuted, fontSize: 12 }}>{t.format}</div>
                  </div>
                </div>
                <div style={{ marginTop: 8, fontSize: 12, color: colors.textDim, fontFamily: "monospace" }}>{t.location}</div>
                <div style={{ fontSize: 12, color: colors.textMuted, marginTop: 4 }}>{t.note}</div>
              </div>
            ))}

            <div style={{ marginTop: 24 }}>
              <StageButton
                label="Proceed to QA →"
                onClick={() => completeStage(3)}
                disabled={!trackData.archiveWav || !trackData.distroWav || !trackData.webMp3}
              />
            </div>
          </div>
        );

      case "qa":
        return (
          <div>
            <h3 style={{ color: colors.gold, margin: "0 0 8px", fontSize: 18 }}>Quality Assurance</h3>
            <p style={{ color: colors.textMuted, margin: "0 0 20px", lineHeight: 1.6, fontSize: 14 }}>
              Listen through the full mastered track. Check every item before proceeding.
            </p>

            <div style={{
              padding: 12, marginBottom: 20, borderRadius: 8, background: `${colors.purpleDim}22`,
              display: "flex", alignItems: "center", justifyContent: "space-between",
            }}>
              <span style={{ color: colors.textMuted, fontSize: 13 }}>Progress</span>
              <span style={{ color: allQaPassed ? colors.green : colors.orange, fontWeight: 700, fontSize: 14 }}>
                {Object.values(trackData.qaChecks).filter(Boolean).length} / {QA_CHECKS.length}
              </span>
            </div>

            {QA_CHECKS.map(check => (
              <div
                key={check.id}
                onClick={() => toggleQA(check.id)}
                style={{
                  padding: "12px 14px", marginBottom: 8, borderRadius: 8, cursor: "pointer",
                  background: trackData.qaChecks[check.id] ? `${colors.greenDim}22` : colors.bg,
                  border: `1px solid ${trackData.qaChecks[check.id] ? colors.green : colors.border}`,
                  display: "flex", alignItems: "center", gap: 12, transition: "all 0.15s ease",
                }}
              >
                <div style={{
                  width: 22, height: 22, borderRadius: 5, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: trackData.qaChecks[check.id] ? colors.green : "transparent",
                  border: `2px solid ${trackData.qaChecks[check.id] ? colors.green : colors.textDim}`,
                  fontSize: 12, color: colors.text,
                }}>
                  {trackData.qaChecks[check.id] ? "✓" : ""}
                </div>
                <span style={{
                  color: trackData.qaChecks[check.id] ? colors.text : colors.textMuted,
                  fontSize: 13, lineHeight: 1.5,
                  textDecoration: trackData.qaChecks[check.id] ? "line-through" : "none",
                  opacity: trackData.qaChecks[check.id] ? 0.7 : 1,
                }}>
                  {check.label}
                </span>
              </div>
            ))}

            <div style={{ marginTop: 24 }}>
              <StageButton label="Proceed to Website →" onClick={() => completeStage(4)} disabled={!allQaPassed} />
            </div>
          </div>
        );

      case "website":
        return (
          <div>
            <h3 style={{ color: colors.gold, margin: "0 0 8px", fontSize: 18 }}>Website Deployment</h3>
            <p style={{ color: colors.textMuted, margin: "0 0 20px", lineHeight: 1.6, fontSize: 14 }}>
              Deploy the 320kbps MP3 to the Eleventy site at <strong style={{ color: colors.purpleLight }}>words-of-plainness.vercel.app</strong>.
            </p>

            <div style={{ background: colors.bg, borderRadius: 10, border: `1px solid ${colors.border}`, padding: 16, marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: colors.textMuted, fontWeight: 700, marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>
                Deployment Steps
              </div>
              {[
                `Copy ${getFilename()}.mp3 to src/assets/audio/`,
                trackData.prefixType === "##"
                  ? "Update chapter YAML front matter (audio.testimony section)"
                  : "Add to Music page configuration for non-chapter tracks",
                'git add . && git commit -m "Add [track]" && git push origin main',
                "vercel --prod",
                "Verify playback on live site (cache-bust if needed: ?v=2)",
              ].map((step, i) => (
                <div key={i} style={{ display: "flex", gap: 12, marginBottom: 10, alignItems: "flex-start" }}>
                  <span style={{
                    width: 22, height: 22, borderRadius: "50%", flexShrink: 0,
                    background: colors.purpleDim, color: colors.purpleLight,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 11, fontWeight: 700,
                  }}>{i + 1}</span>
                  <span style={{ color: colors.textMuted, fontSize: 13, fontFamily: i >= 2 && i <= 3 ? "monospace" : "inherit", lineHeight: 1.5 }}>
                    {step}
                  </span>
                </div>
              ))}
            </div>

            <div
              onClick={() => update("websiteDeployed", !trackData.websiteDeployed)}
              style={{
                padding: 16, borderRadius: 10, cursor: "pointer",
                background: trackData.websiteDeployed ? `${colors.greenDim}33` : colors.bg,
                border: `1px solid ${trackData.websiteDeployed ? colors.green : colors.border}`,
                display: "flex", alignItems: "center", gap: 12,
              }}
            >
              <div style={{
                width: 24, height: 24, borderRadius: 6,
                background: trackData.websiteDeployed ? colors.green : "transparent",
                border: `2px solid ${trackData.websiteDeployed ? colors.green : colors.textDim}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 14, color: colors.text,
              }}>
                {trackData.websiteDeployed ? "✓" : ""}
              </div>
              <span style={{ color: colors.text, fontWeight: 600, fontSize: 14 }}>Website deployment confirmed</span>
            </div>

            <div style={{ marginTop: 24 }}>
              <StageButton label="Proceed to DistroKid →" onClick={() => completeStage(5)} disabled={!trackData.websiteDeployed} />
            </div>
          </div>
        );

      case "distrokid":
        return (
          <div>
            <h3 style={{ color: colors.gold, margin: "0 0 8px", fontSize: 18 }}>DistroKid Upload</h3>
            <p style={{ color: colors.textMuted, margin: "0 0 20px", lineHeight: 1.6, fontSize: 14 }}>
              Upload the Distribution WAV to DistroKid. Enable recommended add-ons.
            </p>

            <div style={{ background: colors.bg, borderRadius: 10, border: `1px solid ${colors.border}`, padding: 16, marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: colors.textMuted, fontWeight: 700, marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>
                DistroKid Settings
              </div>
              {[
                { setting: "Artist Name", value: "Words of Plainness" },
                { setting: "Leave a Legacy", value: "Enable ($29/single) — keeps music live if subscription lapses" },
                { setting: "YouTube Content ID", value: "Enable — monetizes & tracks usage" },
                { setting: "Shazam", value: "Enable" },
                { setting: "Lyrics", value: "Submit for Spotify/Apple display" },
                { setting: "Store Pricing", value: "Standard" },
              ].map((s, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: i < 5 ? `1px solid ${colors.border}` : "none" }}>
                  <span style={{ color: colors.textMuted, fontSize: 13 }}>{s.setting}</span>
                  <span style={{ color: colors.purpleLight, fontSize: 13, fontWeight: 600, textAlign: "right", maxWidth: "55%" }}>{s.value}</span>
                </div>
              ))}
            </div>

            <Input label="ISRC Code (auto-generated by DistroKid)" field="isrc" value={trackData.isrc} onChange={update} placeholder="e.g., USXX12600001" />
            <Input label="Release Date" field="releaseDate" value={trackData.releaseDate} onChange={update} placeholder="YYYY-MM-DD" type="date" />

            <div style={{
              marginTop: 12, padding: 14, background: `${colors.goldDim}22`, borderRadius: 8,
              border: `1px solid ${colors.goldDim}`, fontSize: 13, color: colors.gold, lineHeight: 1.6,
            }}>
              ⚠️ <strong>AI-Content Policy:</strong> Verify current platform policies before submitting. Aaron's role as Producer/Lyricist/Creative Director is the strongest framing. AI tools = session musicians executing human creative vision.
            </div>

            <div
              onClick={() => update("distrokidUploaded", !trackData.distrokidUploaded)}
              style={{
                padding: 16, marginTop: 16, borderRadius: 10, cursor: "pointer",
                background: trackData.distrokidUploaded ? `${colors.greenDim}33` : colors.bg,
                border: `1px solid ${trackData.distrokidUploaded ? colors.green : colors.border}`,
                display: "flex", alignItems: "center", gap: 12,
              }}
            >
              <div style={{
                width: 24, height: 24, borderRadius: 6,
                background: trackData.distrokidUploaded ? colors.green : "transparent",
                border: `2px solid ${trackData.distrokidUploaded ? colors.green : colors.textDim}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 14, color: colors.text,
              }}>
                {trackData.distrokidUploaded ? "✓" : ""}
              </div>
              <span style={{ color: colors.text, fontWeight: 600, fontSize: 14 }}>DistroKid upload confirmed</span>
            </div>

            <div style={{ marginTop: 24 }}>
              <StageButton label="Mark as Published ✓" onClick={() => { completeStage(6); addToCatalog(); }} disabled={!trackData.distrokidUploaded} />
            </div>
          </div>
        );

      case "publish":
        return (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <div style={{ fontSize: 64, marginBottom: 16 }}>🎉</div>
            <h3 style={{ color: colors.gold, margin: "0 0 8px", fontSize: 22 }}>Published!</h3>
            <p style={{ color: colors.textMuted, margin: "0 0 24px", lineHeight: 1.6, fontSize: 14 }}>
              <strong style={{ color: colors.text }}>{trackData.title}</strong> is now in the DistroKid pipeline.
              Allow 2–5 days for delivery to streaming platforms.
            </p>

            <div style={{
              background: colors.bg, borderRadius: 10, border: `1px solid ${colors.border}`,
              padding: 16, textAlign: "left", marginBottom: 24, fontFamily: "'JetBrains Mono', monospace", fontSize: 13,
            }}>
              <div style={{ color: colors.textDim, marginBottom: 8 }}>CATALOG ENTRY</div>
              <div style={{ color: colors.purpleLight }}>{getFilename()}.wav</div>
              {trackData.isrc && <div style={{ color: colors.textMuted, marginTop: 4 }}>ISRC: {trackData.isrc}</div>}
              {trackData.releaseDate && <div style={{ color: colors.textMuted, marginTop: 4 }}>Release: {trackData.releaseDate}</div>}
            </div>

            <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
              <StageButton label="Process Another Track" onClick={resetPipeline} />
              <StageButton label="View Catalog" onClick={() => setShowCatalog(true)} variant="secondary" />
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  // ─── MAIN RENDER ───────────────────────────────────────────────
  return (
    <div style={{
      minHeight: "100vh", background: colors.bg, color: colors.text,
      fontFamily: "'Inter', -apple-system, sans-serif",
    }}>
      {/* HEADER */}
      <div style={{
        padding: "20px 24px", borderBottom: `1px solid ${colors.border}`,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 18, fontWeight: 800, letterSpacing: -0.5 }}>
            <span style={{ color: colors.gold }}>WoP</span>{" "}
            <span style={{ color: colors.textMuted, fontWeight: 400 }}>Publication Pipeline</span>
          </h1>
          <div style={{ fontSize: 11, color: colors.textDim, marginTop: 2 }}>
            Masterchannel → DistroKid • v1.0
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {catalog.length > 0 && (
            <button
              onClick={() => setShowCatalog(!showCatalog)}
              style={{
                padding: "8px 14px", borderRadius: 8, border: `1px solid ${colors.border}`,
                background: showCatalog ? colors.surfaceHover : "transparent", cursor: "pointer",
                color: colors.textMuted, fontSize: 12, fontWeight: 600,
              }}
            >
              📋 Catalog ({catalog.length})
            </button>
          )}
        </div>
      </div>

      {/* CATALOG MODAL */}
      {showCatalog && catalog.length > 0 && (
        <div style={{
          padding: 20, margin: "0 24px", marginTop: 16, background: colors.surface, borderRadius: 12,
          border: `1px solid ${colors.border}`,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h3 style={{ margin: 0, color: colors.gold, fontSize: 16 }}>Published Catalog</h3>
            <button onClick={() => setShowCatalog(false)} style={{ background: "none", border: "none", color: colors.textDim, cursor: "pointer", fontSize: 18 }}>×</button>
          </div>
          {catalog.map((entry, i) => (
            <div key={i} style={{
              padding: 12, marginBottom: 8, background: colors.bg, borderRadius: 8,
              border: `1px solid ${colors.border}`, fontSize: 13,
            }}>
              <div style={{ color: colors.purpleLight, fontFamily: "monospace", fontWeight: 600 }}>{entry.filename}</div>
              <div style={{ color: colors.textMuted, marginTop: 4 }}>
                {entry.isrc && <span>ISRC: {entry.isrc} • </span>}
                {entry.releaseDate && <span>Release: {entry.releaseDate}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", maxWidth: 1100, margin: "0 auto", padding: "24px 24px" }}>
        {/* STAGE NAV */}
        <div style={{ width: 200, flexShrink: 0, marginRight: 32 }}>
          {STAGES.map((stage, idx) => {
            const isActive = idx === currentStage;
            const isComplete = completedStages.has(idx);
            const isAccessible = idx <= currentStage || completedStages.has(idx);

            return (
              <div
                key={stage.id}
                onClick={() => isAccessible && setCurrentStage(idx)}
                style={{
                  padding: "12px 14px", marginBottom: 4, borderRadius: 10, cursor: isAccessible ? "pointer" : "default",
                  background: isActive ? colors.surface : "transparent",
                  border: `1px solid ${isActive ? colors.borderActive : "transparent"}`,
                  opacity: isAccessible ? 1 : 0.35, transition: "all 0.2s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 16 }}>{isComplete && !isActive ? "✅" : stage.icon}</span>
                  <div>
                    <div style={{
                      fontSize: 13, fontWeight: isActive ? 700 : 500,
                      color: isActive ? colors.text : isComplete ? colors.green : colors.textMuted,
                    }}>
                      {stage.label}
                    </div>
                    <div style={{ fontSize: 10, color: colors.textDim, marginTop: 1 }}>{stage.desc}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* MAIN CONTENT */}
        <div style={{
          flex: 1, background: colors.surface, borderRadius: 14,
          border: `1px solid ${colors.border}`, padding: 28, minHeight: 500,
        }}>
          {/* Stage header bar */}
          <div style={{
            display: "flex", alignItems: "center", gap: 8, marginBottom: 24,
            padding: "10px 14px", background: `${colors.purpleDim}22`, borderRadius: 8,
          }}>
            <span style={{ fontSize: 20 }}>{STAGES[currentStage].icon}</span>
            <span style={{ fontSize: 11, color: colors.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
              Step {currentStage + 1} of {STAGES.length}
            </span>
            <div style={{
              flex: 1, height: 4, background: colors.border, borderRadius: 2, marginLeft: 12,
              overflow: "hidden",
            }}>
              <div style={{
                height: "100%", borderRadius: 2,
                background: `linear-gradient(90deg, ${colors.purple}, ${colors.purpleLight})`,
                width: `${((currentStage + 1) / STAGES.length) * 100}%`,
                transition: "width 0.4s ease",
              }} />
            </div>
          </div>

          {renderStage()}
        </div>
      </div>

      {/* FOOTER */}
      <div style={{
        padding: "16px 24px", textAlign: "center", color: colors.textDim, fontSize: 11,
        borderTop: `1px solid ${colors.border}`, marginTop: 40,
      }}>
        Words of Plainness Ministry • Publication Pipeline v1.0 •{" "}
        <span style={{ color: colors.gold, fontStyle: "italic" }}>"For my soul delighteth in plainness"</span>{" "}
        — 2 Nephi 31:3
      </div>
    </div>
  );
}
