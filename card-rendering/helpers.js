/* =======================================================
 * IconsHelper Module
 * Provides mana symbol lookup and mana cost parsing.
 * ======================================================= */
const IconsHelper = (() => {
  const mana_symbols = {
    "{0}": { svg_uri: "assets/img/symbols/0.svg" },
    "{1}": { svg_uri: "assets/img/symbols/1.svg" },
    "{2}": { svg_uri: "assets/img/symbols/2.svg" },
    "{2B}": { svg_uri: "assets/img/symbols/2B.svg" },
    "{2G}": { svg_uri: "assets/img/symbols/2G.svg" },
    "{2R}": { svg_uri: "assets/img/symbols/2R.svg" },
    "{2U}": { svg_uri: "assets/img/symbols/2U.svg" },
    "{2W}": { svg_uri: "assets/img/symbols/2W.svg" },
    "{3}": { svg_uri: "assets/img/symbols/3.svg" },
    "{4}": { svg_uri: "assets/img/symbols/4.svg" },
    "{5}": { svg_uri: "assets/img/symbols/5.svg" },
    "{6}": { svg_uri: "assets/img/symbols/6.svg" },
    "{7}": { svg_uri: "assets/img/symbols/7.svg" },
    "{8}": { svg_uri: "assets/img/symbols/8.svg" },
    "{9}": { svg_uri: "assets/img/symbols/9.svg" },
    "{10}": { svg_uri: "assets/img/symbols/10.svg" },
    "{11}": { svg_uri: "assets/img/symbols/11.svg" },
    "{12}": { svg_uri: "assets/img/symbols/12.svg" },
    "{13}": { svg_uri: "assets/img/symbols/13.svg" },
    "{14}": { svg_uri: "assets/img/symbols/14.svg" },
    "{15}": { svg_uri: "assets/img/symbols/15.svg" },
    "{16}": { svg_uri: "assets/img/symbols/16.svg" },
    "{17}": { svg_uri: "assets/img/symbols/17.svg" },
    "{18}": { svg_uri: "assets/img/symbols/18.svg" },
    "{19}": { svg_uri: "assets/img/symbols/19.svg" },
    "{20}": { svg_uri: "assets/img/symbols/20.svg" },
    "{100}": { svg_uri: "assets/img/symbols/100.svg" },
    "{1000000}": { svg_uri: "assets/img/symbols/1000000.svg" },
    "{A}": { svg_uri: "assets/img/symbols/A.svg" },
    "{B}": { svg_uri: "assets/img/symbols/B.svg" },
    "{BG}": { svg_uri: "assets/img/symbols/BG.svg" },
    "{BGP}": { svg_uri: "assets/img/symbols/BGP.svg" },
    "{BR}": { svg_uri: "assets/img/symbols/BR.svg" },
    "{BRP}": { svg_uri: "assets/img/symbols/BRP.svg" },
    "{C}": { svg_uri: "assets/img/symbols/C.svg" },
    "{CB}": { svg_uri: "assets/img/symbols/CB.svg" },
    "{CG}": { svg_uri: "assets/img/symbols/CG.svg" },
    "{CHAOS}": { svg_uri: "assets/img/symbols/CHAOS.svg" },
    "{CP}": { svg_uri: "assets/img/symbols/CP.svg" },
    "{CR}": { svg_uri: "assets/img/symbols/CR.svg" },
    "{CU}": { svg_uri: "assets/img/symbols/CU.svg" },
    "{CW}": { svg_uri: "assets/img/symbols/CW.svg" },
    "{D}": { svg_uri: "assets/img/symbols/D.svg" },
    "{E}": { svg_uri: "assets/img/symbols/E.svg" },
    "{G}": { svg_uri: "assets/img/symbols/G.svg" },
    "{GU}": { svg_uri: "assets/img/symbols/GU.svg" },
    "{GUP}": { svg_uri: "assets/img/symbols/GUP.svg" },
    "{GW}": { svg_uri: "assets/img/symbols/GW.svg" },
    "{GWP}": { svg_uri: "assets/img/symbols/GWP.svg" },
    "{H}": { svg_uri: "assets/img/symbols/H.svg" },
    "{HALF}": { svg_uri: "assets/img/symbols/HALF.svg" },
    "{HR}": { svg_uri: "assets/img/symbols/HR.svg" },
    "{HW}": { svg_uri: "assets/img/symbols/HW.svg" },
    "{INFINITY}": { svg_uri: "assets/img/symbols/INFINITY.svg" },
    "{L}": { svg_uri: "assets/img/symbols/L.svg" },
    "{P}": { svg_uri: "assets/img/symbols/P.svg" },
    "{PW}": { svg_uri: "assets/img/symbols/PW.svg" },
    "{Q}": { svg_uri: "assets/img/symbols/Q.svg" },
    "{R}": { svg_uri: "assets/img/symbols/R.svg" },
    "{RG}": { svg_uri: "assets/img/symbols/RG.svg" },
    "{RGP}": { svg_uri: "assets/img/symbols/RGP.svg" },
    "{RP}": { svg_uri: "assets/img/symbols/RP.svg" },
    "{RW}": { svg_uri: "assets/img/symbols/RW.svg" },
    "{RWP}": { svg_uri: "assets/img/symbols/RWP.svg" },
    "{S}": { svg_uri: "assets/img/symbols/S.svg" },
    "{T}": { svg_uri: "assets/img/symbols/T.svg" },
    "{TK}": { svg_uri: "assets/img/symbols/TK.svg" },
    "{U}": { svg_uri: "assets/img/symbols/U.svg" },
    "{UB}": { svg_uri: "assets/img/symbols/UB.svg" },
    "{UBP}": { svg_uri: "assets/img/symbols/UBP.svg" },
    "{UP}": { svg_uri: "assets/img/symbols/UP.svg" },
    "{UR}": { svg_uri: "assets/img/symbols/UR.svg" },
    "{URP}": { svg_uri: "assets/img/symbols/URP.svg" },
    "{W}": { svg_uri: "assets/img/symbols/W.svg" },
    "{WB}": { svg_uri: "assets/img/symbols/WB.svg" },
    "{WBP}": { svg_uri: "assets/img/symbols/WBP.svg" },
    "{WP}": { svg_uri: "assets/img/symbols/WP.svg" },
    "{WU}": { svg_uri: "assets/img/symbols/WU.svg" },
    "{WUP}": { svg_uri: "assets/img/symbols/WUP.svg" },
    "{X}": { svg_uri: "assets/img/symbols/X.svg" },
    "{Y}": { svg_uri: "assets/img/symbols/Y.svg" },
    "{Z}": { svg_uri: "assets/img/symbols/Z.svg" }
  };

  function getManaIcon(symbol) {
    return mana_symbols[symbol] ? mana_symbols[symbol].svg_uri : "";
  }

  function parseManaCost(manaCostString) {
    const manaRegex = /{([^}]+)}/g;
    let icons = [];
    let match;
    while ((match = manaRegex.exec(manaCostString)) !== null) {
      icons.push(getManaIcon(`{${match[1]}}`));
    }
    return icons;
  }

  return { getManaIcon, parseManaCost, mana_symbols };
})();

/* =======================================================
 * Sets Class
 * Handles set icon logic.
 * ======================================================= */
class Sets {
  constructor() {
    this.setsWithIcons = [
      "med", "m3c", "mb2", "9ed", "cmd", "m11", "vma", "8ed", "mkc", "ddp", "m12",
      "ons", "c18", "eld", "zen", "rvr", "evg", "bro", "bbd", "anb", "mm2", "ha4",
      "uma", "dds", "dom", "m13", "scg", "otj", "dst", "dsc", "und", "c15", "ddm",
      "gnt", "big", "mkm", "c19", "m19", "mat", "v14", "tpr", "con", "c17", "exp",
      "m14", "woe", "mid", "w17", "wwk", "ema", "avr", "iko", "mh1", "afr", "thb",
      "blc", "tsb", "ddd", "v13", "m21", "ha5", "dsk", "ncc", "ktk", "c16", "khm",
      "nph", "som", "ddt", "jou", "mb1", "mm3", "mom", "pip", "5dn", "fdc", "fut",
      "moc", "afc", "ddu", "ltc", "stx", "ths", "mma", "spg", "j22", "ddn", "unh",
      "xln", "wot", "grn", "lgn", "rix", "dmu", "m15", "clu", "cns", "cc1", "h09",
      "v09", "v12", "cn2", "ddo", "e02", "v17", "sis", "pd2", "bng", "bot", "otc",
      "gn3", "cma", "vow", "me2", "lcc", "40k", "dis", "m10", "sta", "2xm", "ha3",
      "chk", "me3", "mic", "soi", "dka", "v15", "gn2", "war", "j21", "voc", "ddj",
      "jud", "znr", "ust", "acr", "c13", "ltr", "ddi", "g18", "plc", "rex", "rtr",
      "w16", "ddc", "ala", "hou", "ori", "fdn", "10e", "c21", "j25", "dd2", "roe",
      "sir", "ha2", "aer", "cm2", "snc", "ss2", "znc", "ddl", "gpt", "jmp", "v16",
      "m20", "drb", "v11", "md1", "cmm", "lrw", "bok", "mor", "tsp", "mh2", "ima",
      "nec", "eve", "dgm", "dde", "dmc", "tor", "brr", "2x2", "neo", "ha1", "rna",
      "zne", "cmr", "ss1", "bfz", "dtk", "sch", "gtc", "c14", "mh3", "ddg", "mrd",
      "csp", "a25", "frf", "c20", "ddk", "kld", "akr", "blb", "lci", "v10", "isd",
      "akh", "sld", "sok", "cm1", "khc", "mul", "who", "ddq", "tsr", "woc", "clb",
      "dmr", "me4", "klr", "pd3", "one", "onc", "ddf", "hop", "otp", "emn", "gs1",
      "gdy", "ddh", "arb", "arc", "shm", "e01", "ddr", "pc2", "pca", "brc", "hbg",
      "ogw", "rav", "mbs"
    ];
  }

  hasIcon(setCode) {
    return this.setsWithIcons.includes(setCode);
  }

  getSetIconUri(card) {
    if (card.set_icon) {
      return card.set_icon;
    } else if (this.hasIcon(card.set)) {
      return `assets/img/set_icons/${card.set}_${card.rarity || "common"}.webp`;
    } else {
      return "";
    }
  }
}

const setsHelper = new Sets();