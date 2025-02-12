/* =======================================================
 * Utility Functions
 * =======================================================
 */

/**
 * Replaces mana symbols in the oracle text with <img> tags
 * and wraps text in parentheses with a span.
 */
function parseOracle(str) {
  const manaRegex = /{([^}]+)}/g;
  str = str.replace(manaRegex, (match, group) => {
    const key = `{${group}}`;
    const iconUri = IconsHelper.getManaIcon(key);
    return iconUri ? `<img src="${iconUri}" class="ms">` : match;
  });
  // Wrap text in parentheses with a special class.
  str = str.replace(/\([^)]+\)/g, (match) => `<span class="oracle-reminder">${match}</span>`);
  return str;
}

/**
 * Resizes text horizontally until it fits within its container.
 */
function resizeTextHorizontally(el) {
  const computedStyle = window.getComputedStyle(el);
  let fontSize = parseFloat(computedStyle.fontSize);
  el.style.fontSize = fontSize + "px";
  while (el.scrollWidth > el.clientWidth && fontSize > 4) {
    fontSize -= 0.5;
    el.style.fontSize = fontSize + "px";
  }
}

/**
 * Helper function that returns true if the given string contains
 * any of the search terms (case insensitive).
 */
function contains(str, search) {
  if (!str || !search) return false;
  if (Array.isArray(search))
    return search.some(s => str.toLowerCase().includes(s.toLowerCase()));
  return str.toLowerCase().includes(search.toLowerCase());
}

/* =======================================================
 * Card Computation Functions
 * Computes and returns an object with properties derived from the card JSON.
 * =======================================================
 */
function computeCardProps(card, currentFace = 0) {
  let props = {};

  // Determine primary face (for DFC cards) and back face.
  props.card_face = (card.card_faces && card.card_faces.length)
    ? card.card_faces[card.layout === "adventure" ? 0 : currentFace || 0]
    : card;
  props.back_face = (card.card_faces && card.card_faces.length)
    ? card.card_faces[(currentFace + 1) % 2]
    : card;

  // Determine type booleans.
  props.is_land = props.card_face.type_line &&
    (props.card_face.type_line.startsWith("Land") ||
     props.card_face.type_line.startsWith("Terrain"));
  props.is_legendary = (card.frame_effects && card.frame_effects.includes("legendary")) ||
    (props.card_face.type_line &&
     (props.card_face.type_line.startsWith("Legendary") ||
      props.card_face.type_line.includes("légendaire")));
  props.is_planeswalker = props.card_face.type_line &&
    props.card_face.type_line.toLowerCase().includes("planeswalker");
  props.has_legendary_crown = props.is_legendary &&
    !props.is_planeswalker &&
    !(card.frame_effects && card.frame_effects.includes("compasslanddfc"));
  props.is_adventure = card.layout === "adventure";
  props.is_saga = props.card_face.layout === "saga" ||
    (props.card_face.type_line && props.card_face.type_line.includes("Saga"));
  props.is_class = props.card_face.layout === "class" ||
    (props.card_face.type_line && props.card_face.type_line.includes("Class"));
  props.is_vehicle = props.card_face.type_line &&
    (props.card_face.type_line.includes("Vehicle") ||
     props.card_face.type_line.includes("Véhicule"));
  props.is_dualfaced = card.card_faces && !props.is_adventure;
  props.is_mdfc = card.layout === "modal_dfc";
  props.is_transform = card.layout === "transform";
  props.is_levelup = props.card_face.oracle_text &&
    (props.card_face.oracle_text.includes("Level up") ||
     props.card_face.oracle_text.includes("Montée de niveau"));

  // Parse mana cost using our IconsHelper module.
  props.mana_cost = props.card_face.mana_cost
    ? IconsHelper.parseManaCost(props.card_face.mana_cost)
    : [];

  // Adventure or modal back mana cost.
  props.adventure_mana_cost = [];
  if (card.card_faces && card.card_faces[1] && card.card_faces[1].mana_cost) {
    props.adventure_mana_cost = IconsHelper.parseManaCost(card.card_faces[1].mana_cost);
  }
  props.mdfc_back_mana_cost = [];
  if (
    card.card_faces &&
    card.card_faces[(currentFace + 1) % 2] &&
    card.card_faces[(currentFace + 1) % 2].mana_cost
  ) {
    props.mdfc_back_mana_cost = IconsHelper.parseManaCost(card.card_faces[(currentFace + 1) % 2].mana_cost);
  }

  // MDFC hint text.
  if (props.card_face.mdfc_hint)
    props.mdfc_hint_text = props.card_face.mdfc_hint;
  else if (props.back_face.type_line)
    props.mdfc_hint_text = props.back_face.type_line.substr(props.back_face.type_line.indexOf("—") + 1).trim();
  else
    props.mdfc_hint_text = "";

  // Extended art detection.
  props.extended_art = ["extended", "full", "full-footer"].includes(props.card_face.art_variant);

  // Oracle text and flavor text.
  props.oracle_lines = props.card_face.oracle_text
    ? props.card_face.oracle_text.split("\n").map(parseOracle)
    : [];
  props.adventure_oracle_lines = (card.card_faces && card.card_faces[1] && card.card_faces[1].oracle_text)
    ? card.card_faces[1].oracle_text.split("\n").map(parseOracle)
    : [];
  props.saga_reminder = props.card_face.oracle_text
    ? parseOracle(props.card_face.oracle_text.split("\n")[0])
    : "";
  props.class_reminder = props.saga_reminder;
  if (props.card_face.oracle_text) {
    let steps = props.card_face.oracle_text.split("\n").filter(s => s.match(/^(.+) — /));
    props.saga_steps = steps.map(s => {
      let m = s.match(/(.+) — (.+)/);
      let icons = m[1].split(",").map(s => "assets/img/saga/" + s.trim() + ".webp");
      return { steps: icons, html: parseOracle(m[2]) };
    });
  } else {
    props.saga_steps = [];
  }
  props.class_steps = props.card_face.oracle_text
    ? props.card_face.oracle_text.split("\n").slice(1).map(line => ({
        class: "normal",
        html: parseOracle(line)
      }))
    : [];

  // Planeswalker abilities.
  if (props.is_planeswalker && props.card_face.oracle_text) {
    props.planeswalker_abilities = props.card_face.oracle_text.split("\n").map(line => {
      let ability = { html: parseOracle(line), cost: null };
      let m = line.match(/^[+-−]?(\d+):/);
      if (m) {
        if (line[0] === "0") ability.cost = 0;
        else if (line[0] === "+") ability.cost = parseInt(m[1]);
        else ability.cost = -parseInt(m[1]);
        ability.html = parseOracle(line.substr(m[0].length + 1));
      }
      return ability;
    });
  } else {
    props.planeswalker_abilities = null;
  }

  if (props.is_planeswalker) {
    // For planeswalkers, add a "large" class if there are more than 3 abilities.
    if (props.planeswalker_abilities && props.planeswalker_abilities.length > 3) {
      props.is_large_planeswalker = true;
    } else {
      props.is_large_planeswalker = false;
    }
  }

  // Copyright.
  props.copyright =
    card.copyright || `™ & © ${new Date().getFullYear()} Wizards of the Coast`;

  // Compute colors.
  function computeColors(face) {
    let colors;
    if (face.colors && face.colors.length > 0) colors = face.colors;
    else if (face.color_identity) colors = face.color_identity;
    else if (face.mana_cost) colors = Array.from(face.mana_cost).filter(c => "WUBRG".includes(c));
    else colors = [];
    if (colors.length === 0 && card.color_identity && card.color_identity.length > 0)
      colors = card.color_identity;
    let sorted_colors = [...new Set(colors)]
      .sort((l, r) => "WUBRG".indexOf(l) - "WUBRG".indexOf(r))
      .join("");
    return contains(face.type_line, ["Artifact", "Artefact", "Artéfact"])
      ? "Artifact"
      : sorted_colors.length === 0
        ? "Colourless"
        : sorted_colors.length > 2
          ? "Gold"
          : sorted_colors;
  }
  props.colors = computeColors(props.card_face);

  // Determine boxes colors.
  if (props.is_vehicle) props.boxes_colors = "Vehicle";
  else if (props.is_land)
    props.boxes_colors = props.colors.length > 2 && props.colors.length < 5 ? "Gold" : "Land";
  else
    props.boxes_colors = props.colors.length > 1 && props.colors.length < 5 ? "Gold" : props.colors;

  // Choose background – select folder based on type.
  let folder;
  if (props.is_planeswalker) {
      folder = props.is_large_planeswalker ? "planeswalker_large_bg" : "planeswalker_bg";
  }
  else if (props.is_saga) folder = "saga_bg";
  else if (props.is_class) folder = "saga_bg";
  else if (card.frame_effects && card.frame_effects.includes("compasslanddfc") && currentFace === 1)
    folder = "ixalan_bg";
  else folder = "bg";
  props.background = `url(assets/img/${folder}/${props.is_vehicle ? "Vehicle" : props.boxes_colors}.webp)`;

  // Choose frame image folder.
  if (props.is_adventure) folder = "adventure_frames";
  else if (props.is_saga) folder = "saga_frames";
  else if (props.is_class) folder = "saga_frames";
  else if (props.is_planeswalker) folder = props.is_large_planeswalker ? "planeswalker_large_frames" : "planeswalker_frames";
  else if (props.is_mdfc) folder = "mdfc_frames";
  else if (props.is_transform) folder = currentFace === 0 ? "transform_frames" : "transform_back_frames";
  else folder = "frames";
  if (props.extended_art && !props.is_saga && !props.is_class) folder = "extended_" + folder;
  let frameColor = (props.colors === "Artifact" && props.card_face.colors && props.card_face.colors.length === 1)
      ? props.card_face.colors[0]
      : props.colors;
  props.frame = `url(assets/img/${folder}/${frameColor}.webp)`;

  // Boxes and mid_boxes images.
  folder = props.is_planeswalker
    ? "planeswalker_boxes"
    : props.is_mdfc || props.is_transform
      ? currentFace === 0 ? "mdfc_boxes" : "mdfc_back_boxes"
      : props.extended_art && !props.is_class
        ? "extended_boxes"
        : "boxes";
  props.boxes = `url(assets/img/${folder}/${props.boxes_colors}.webp)`;
  props.mid_boxes = props.extended_art && !props.is_planeswalker && !props.is_class
    ? `url(assets/img/extended_boxes/${props.boxes_colors}.webp)`
    : props.boxes;

  // Legendary crown.
  let crownFolder = props.extended_art ? "extended_legendary_crowns" : "legendary_crowns";
  props.legendary_crown = `url(assets/img/${crownFolder}/${props.boxes_colors}.webp)`;

  // Power/Toughness box.
  let ptFolder = (props.is_mdfc || props.is_transform) && currentFace === 1 ? "transform_back_pt_boxes" : "pt_boxes";
  props.pt_box = `url(assets/img/${ptFolder}/${props.is_vehicle ? "Vehicle" : props.boxes_colors}.webp)`;

  // Saga text box.
  props.saga_text_box = `url(assets/img/saga_textboxes/${props.boxes_colors}.webp)`;

  // MDFC icon and hint.
  props.mdfc_icon = `url(assets/img/mdfc${currentFace === 0 ? "" : "_back"}_icons/${props.boxes_colors === "Land" ? props.colors : props.boxes_colors}.webp)`;
  let hintColors = props.colors;
  if (hintColors.length > 1 && hintColors.length < 5) hintColors = "Gold";
  props.mdfc_hint = `url(assets/img/mdfc${currentFace === 0 ? "" : "_back"}_hints/${hintColors}.webp)`;
  props.mdfc_hint_color = currentFace === 0 ? "white" : "black";

  // Transform icon.
  props.transform_icon = `url(assets/img/transform${currentFace === 0 ? "" : "_back"}_icons/${(card.frame_effects && card.frame_effects[0]) ? card.frame_effects[0] : "sunmoondfc"}.webp)`;

  // Determine power/toughness box color and top/mid line colors.
  props.pt_box_color = props.is_vehicle || (props.is_transform && currentFace === 1) ? "white" : "black";
  if (props.is_mdfc)
    props.top_line_color = currentFace === 0 ? "black" : "white";
  else if (props.is_transform && currentFace === 1 && !props.is_planeswalker)
    props.top_line_color = "white";
  else
    props.top_line_color = "black";
  if ((props.extended_art && !props.is_class && !props.is_planeswalker && (!props.is_transform || currentFace === 0)) ||
      ((props.is_transform || props.is_mdfc) && currentFace === 1 && !props.is_planeswalker))
    props.mid_line_color = "white";
  else
    props.mid_line_color = "black";

  // Color indicator (if available).
  if (props.card_face.color_indicator) {
    let sorted = Array.from(props.card_face.color_indicator)
      .sort((a, b) => "WUBRG".indexOf(a) - "WUBRG".indexOf(b))
      .join("");
    props.color_indicator = `assets/img/color_indicators/${sorted}.webp`;
  } else {
    props.color_indicator = "";
  }

  // Illustration handling – choose art crop if available.
  let artCard = props.is_adventure ? card : props.card_face;
  let artUrl = "";
  if (artCard.image_uris && artCard.image_uris.art_crop && artCard.image_uris.art_crop.trim() !== "") {
    artUrl = artCard.image_uris.art_crop;
  } else {
    artUrl = "assets/img/placeholder-art.webp";
  }
  props.illustration = `url("${artUrl}")`;
  props.illustration_scale = artCard.illustration_scale || 1;
  if (artCard.illustration_position) {
    props.illustration_position = {
      x: artCard.illustration_position.x + "mm",
      y: artCard.illustration_position.y + "mm"
    };
  } else {
    props.illustration_position = { x: "0mm", y: "0mm" };
  }

  // Set icon URI (using the Sets helper defined in helpers.js).
  props.set_icon_uri = setsHelper.getSetIconUri(card);

  // Archive frame colors (simplified).
  let archiveColor = (props.card_face.color_identity && props.card_face.color_identity[0]) ? props.card_face.color_identity[0] : "Gold";
  props.archive_frame_colors = {
    primary: archiveColor,
    lighter: archiveColor,
    darker: archiveColor,
    left: { primary: archiveColor, lighter: archiveColor, darker: archiveColor },
    right: { primary: archiveColor, lighter: archiveColor, darker: archiveColor }
  };

  return props;
}

/* =======================================================
 * Card Rendering Functions
 * =======================================================
 */

/**
 * Sets CSS custom properties on the card element based on computed props.
 */
function setCardStyles(cardEl, props, scale, renderMargin) {
  cardEl.style.setProperty("--bg-image", props.background);
  cardEl.style.setProperty("--frame-image", props.frame);
  cardEl.style.setProperty("--boxes-image", props.boxes);
  cardEl.style.setProperty("--mid-boxes-image", props.mid_boxes);
  cardEl.style.setProperty("--top-line-color", props.top_line_color);
  cardEl.style.setProperty("--mid-line-color", props.mid_line_color);
  cardEl.style.setProperty("--pt-box-image", props.pt_box);
  cardEl.style.setProperty("--pt-box-color", props.pt_box_color);
  cardEl.style.setProperty("--saga-text-box-image", props.saga_text_box);
  cardEl.style.setProperty("--mdfc-icon-image", props.mdfc_icon);
  cardEl.style.setProperty("--mdfc-hint-image", props.mdfc_hint);
  cardEl.style.setProperty("--mdfc-hint-color", props.mdfc_hint_color);
  cardEl.style.setProperty("--transform-icon-image", props.transform_icon);
  cardEl.style.setProperty("--renderMargin", renderMargin);
  cardEl.style.setProperty("--scale", scale);
  cardEl.style.setProperty("--frame-colors-left", props.archive_frame_colors.left.primary);
  cardEl.style.setProperty("--frame-colors-right", props.archive_frame_colors.right.primary);
  cardEl.style.setProperty("--illustration-image", props.illustration);
  cardEl.style.setProperty("--illustration-position-x", props.illustration_position.x);
  cardEl.style.setProperty("--illustration-position-y", props.illustration_position.y);
  cardEl.style.setProperty("--illustration-scale", props.illustration_scale);
}

/**
 * Returns inner HTML for a planeswalker card.
 */
function buildPlaneswalkerCardHTML(props, card) {
  return `
    <div class="inner-background"></div>
    <div class="illustration behind-textbox"></div>
    <div class="planeswalker-oracle-bg"></div>
    <div class="inner-frame"></div>
    <div class="legendary-crown" style="display: none;"></div>
    <div class="top-line">
      <span class="name">${props.card_face.printed_name || props.card_face.name}</span>
      <div class="mana-cost">
        ${props.mana_cost.map(uri => `<img src="${uri}" class="ms">`).join("")}
      </div>
    </div>
    <div class="mid-line">
      ${props.card_face.color_indicator ? `<img class="color-indicator" src="${props.color_indicator}">` : ""}
      <div class="type-line">${props.card_face.type_line}</div>
      ${props.set_icon_uri ? `<div class="set-icon-container"><img class="set-icon" src="${props.set_icon_uri}"></div>` : ""}
    </div>
    <div class="oracle planeswalker-oracle" style="font-size: 6.48pt;">
      ${props.planeswalker_abilities ? props.planeswalker_abilities.map(ability => {
        if (ability.cost !== null) {
          return `<div class="planeswalker-ability planeswalker-ability-with-cost">
                    <div class="planeswalker-ability-cost ${ability.cost > 0 ? "planeswalker-ability-cost-plus" : "planeswalker-ability-cost-minus"}">
                      ${ability.cost > 0 ? "+" + ability.cost : ability.cost}
                    </div>
                    <div class="planeswalker-ability-text">${ability.html}</div>
                  </div>`;
        } else {
          return `<div class="planeswalker-ability">
                    <div class="planeswalker-ability-text">${ability.html}</div>
                  </div>`;
        }
      }).join("") : ""}
    </div>
    <div class="loyalty">${props.card_face.loyalty}</div>
    <div class="footer">
      <div class="footer-left">
        <div class="collector-number">${(props.is_adventure || !props.card_face.collector_number)
            ? card.collector_number
            : props.card_face.collector_number}</div>
        <div>
          ${card.set ? `<span class="set">${card.set.toUpperCase()}</span>` : ""}
          ${card.set && card.lang ? "&nbsp;•&nbsp;" : ""}
          ${card.lang ? `<span class="language">${card.lang.toUpperCase()}</span>` : ""}
          ${card.artist ? '<span class="artist-icon"> a </span>' : ""}
          ${card.artist ? `<span class="artist-name">${card.artist}</span>` : ""}
        </div>
      </div>
      <div class="footer-right">
        <div>&nbsp;</div>
        <div class="copyright">${card.copyright || `™ & © ${new Date().getFullYear()} Wizards of the Coast`}</div>
      </div>
    </div>
  `;
}

/**
 * Returns inner HTML for a default (non-planeswalker) card.
 */
function buildDefaultCardHTML(props, card) {
  return `
    <div class="inner-background"></div>
    <div class="inner-frame"></div>
    <div class="top-line">
      <span class="name">${props.card_face.printed_name || props.card_face.name}</span>
      <div class="mana-cost">
        ${props.mana_cost.map(uri => `<img src="${uri}" class="ms">`).join("")}
      </div>
    </div>
    <div class="mid-line">
      ${props.card_face.color_indicator ? `<img class="color-indicator" src="${props.color_indicator}">` : ""}
      <div class="type-line">${props.card_face.type_line}</div>
      ${props.set_icon_uri ? `<div class="set-icon-container"><img class="set-icon" src="${props.set_icon_uri}"></div>` : ""}
    </div>
    <div class="illustration"></div>
    <div class="oracle normal-oracle">
      ${props.oracle_lines.map(line => `<div class="oracle-inner">${line}</div>`).join("")}
      ${props.card_face.flavor_text ? `<div class="oracle-flavor"><hr>${props.card_face.flavor_text}</div>` : ""}
    </div>
    ${props.card_face.power !== undefined && props.card_face.toughness !== undefined
      ? `<div class="pt-box">
           <span>${props.card_face.power}</span>/<span>${props.card_face.toughness}</span>
         </div>`
      : ""}
    <div class="footer">
      <div class="footer-left">
        <div class="collector-number">${(props.is_adventure || !props.card_face.collector_number)
            ? card.collector_number
            : props.card_face.collector_number}</div>
        <div>
          ${card.set ? `<span class="set">${card.set.toUpperCase()}</span>` : ""}
          ${card.set && card.lang ? "&nbsp;•&nbsp;" : ""}
          ${card.lang ? `<span class="language">${card.lang.toUpperCase()}</span>` : ""}
          ${card.artist ? '<span class="artist-icon"> a </span>' : ""}
          ${card.artist ? `<span class="artist-name">${card.artist}</span>` : ""}
        </div>
      </div>
      <div class="footer-right">
        <div>&nbsp;</div>
        <div class="copyright">${card.copyright || `™ & © ${new Date().getFullYear()} Wizards of the Coast`}</div>
      </div>
    </div>
  `;
}

/* =======================================================
 * Main Card Creation Function
 * =======================================================
 */
function createMTGCard(card, scale = 1, renderMargin = 1) {
  const currentFace = 0;
  const props = computeCardProps(card, currentFace);
  const cardEl = document.createElement("div");
  cardEl.className = "mtg-card";

  // Add special classes for planeswalker and legendary cards.
  if (props.is_planeswalker) {
    cardEl.classList.add("planeswalker");
    // For planeswalkers, add a "large" class if there are more than 3 abilities.
    if (props.is_large_planeswalker) {
      cardEl.classList.add("planeswalker-large");
    }
  }
  if (props.is_legendary) {
    cardEl.classList.add("legendary");
  }

  // Set CSS custom properties.
  setCardStyles(cardEl, props, scale, renderMargin);

  // Build inner HTML based on whether the card is a planeswalker.
  cardEl.innerHTML = props.is_planeswalker
    ? buildPlaneswalkerCardHTML(props, card)
    : buildDefaultCardHTML(props, card);

  // Set illustration background on the appropriate element.
  const illustrationDiv = cardEl.querySelector(".illustration, .illustration.behind-textbox");
  if (illustrationDiv) {
    illustrationDiv.style.backgroundImage = props.illustration;
    illustrationDiv.style.backgroundSize = `calc(${props.illustration_scale} * 100%)`;
    illustrationDiv.style.backgroundPosition = `${props.illustration_position.x} ${props.illustration_position.y}`;
    illustrationDiv.style.backgroundRepeat = "no-repeat";
  }

  // Resize text for the card name.
  const nameEl = cardEl.querySelector('.name');
  if (nameEl) {
    resizeTextHorizontally(nameEl);
    const nameObserver = new MutationObserver(() => resizeTextHorizontally(nameEl));
    nameObserver.observe(nameEl, { childList: true, subtree: true, characterData: true });
  }
  // Resize text for the type line.
  const typeLineEl = cardEl.querySelector('.type-line');
  if (typeLineEl) {
    resizeTextHorizontally(typeLineEl);
    const typeLineObserver = new MutationObserver(() => resizeTextHorizontally(typeLineEl));
    typeLineObserver.observe(typeLineEl, { childList: true, subtree: true, characterData: true });
  }

  // For non-planeswalker cards, adjust the oracle text size vertically if needed.
  if (!props.is_planeswalker) {
    const oracle = cardEl.querySelector('.oracle');
    if (oracle) {
      let fontSize = 1; // initial em value
      oracle.style.fontSize = `${fontSize}em`;
      const resizeOracleText = () => {
        oracle.style.fontSize = `${fontSize}em`;
        while (oracle.scrollHeight > oracle.clientHeight && fontSize > 0.5) {
          fontSize -= 0.05;
          oracle.style.fontSize = `${fontSize}em`;
        }
      };
      resizeOracleText();
      const oracleObserver = new MutationObserver(resizeOracleText);
      oracleObserver.observe(oracle, { childList: true, subtree: true, characterData: true });
      const oracleResizeObserver = new ResizeObserver(resizeOracleText);
      oracleResizeObserver.observe(cardEl);
    }
  }

  return cardEl;
}

/* =======================================================
 * Event Listener: Render Card on Click
 * =======================================================
 */
document.getElementById("render-button").addEventListener("click", function () {
  const jsonText = document.getElementById("card-json").value;
  let card;
  try {
    card = JSON.parse(jsonText);
  } catch (e) {
    alert("Invalid JSON: " + e.message);
    return;
  }
  const container = document.getElementById("card-container");
  container.innerHTML = "";
  container.appendChild(createMTGCard(card, 1, 1));
});
