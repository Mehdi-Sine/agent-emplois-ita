import type { Offer, TypologyProfile } from "@/types";

const PROFILE_DEFINITIONS: Array<{
  id: string;
  label: string;
  description: string;
  keywords: string[];
  skills: string[];
  missions: string[];
  activities: string[];
  training: string[];
}> = [
  {
    id: "recherche-experimentation",
    label: "Recherche, expérimentation et R&D appliquée",
    description: "Conception et conduite d'essais, production de références techniques et appui scientifique aux filières.",
    keywords: ["recherche", "r&d", "rd", "expérimentation", "experimentation", "essai", "essais", "station", "ingénieur d'étude", "ingenieur d'etude", "chargé d'étude", "charge d'etude", "scientifique", "agronome", "zootechnie", "phytopathologie"],
    skills: ["Protocole expérimental", "Analyse agronomique ou zootechnique", "Méthodes statistiques", "Rédaction de références techniques"],
    missions: ["Définir des protocoles d'essais", "Piloter des expérimentations terrain, laboratoire ou station", "Analyser les résultats et produire des recommandations", "Valoriser les connaissances auprès des filières"],
    activities: ["Essais variétaux ou systèmes", "Mesures terrain", "Synthèses techniques", "Partenariats de recherche"],
    training: ["Ingénieur agronome/agri-agro", "Master sciences du vivant, productions végétales ou animales", "Doctorat selon séniorité scientifique"],
  },
  {
    id: "conseil-animation-filiere",
    label: "Conseil, animation de filière et transfert",
    description: "Accompagnement des professionnels, animation de réseaux et diffusion opérationnelle des innovations.",
    keywords: ["conseil", "conseiller", "animation", "animateur", "animatrice", "filière", "filiere", "transfert", "formation", "référent", "referent", "accompagnement", "développement", "developpement", "diffusion"],
    skills: ["Animation de collectifs", "Pédagogie et vulgarisation", "Connaissance des filières agricoles", "Gestion de partenariats"],
    missions: ["Animer des groupes de producteurs ou partenaires", "Construire des supports de conseil", "Organiser des journées techniques", "Favoriser l'appropriation des innovations"],
    activities: ["Webinaires et formations", "Visites terrain", "Réseaux d'acteurs", "Veille et capitalisation"],
    training: ["Ingénieur agricole/agronome", "Licence pro ou master conseil agricole", "Expérience terrain en organisme agricole"],
  },
  {
    id: "data-numerique",
    label: "Data, numérique et outils d'aide à la décision",
    description: "Exploitation des données, développement d'outils numériques et modélisation pour l'aide à la décision.",
    keywords: ["data", "donnée", "donnee", "données", "donnees", "numérique", "numerique", "informatique", "développeur", "developpeur", "web", "logiciel", "application", "modélisation", "modelisation", "sig", "géomatique", "geomatique", "biostat", "statistique", "ia", "machine learning", "outil d'aide"],
    skills: ["Gestion et qualité des données", "Statistiques, modélisation ou SIG", "Développement d'applications ou scripts", "Compréhension des usages métier agricoles"],
    missions: ["Structurer et fiabiliser des jeux de données", "Développer ou maintenir des outils métiers", "Produire des analyses et tableaux de bord", "Appuyer les équipes projets sur les méthodes numériques"],
    activities: ["ETL et bases de données", "Cartographie", "Modèles prédictifs", "Interfaces web ou outils OAD"],
    training: ["Master data science/statistiques/SIG", "École d'ingénieur informatique ou agronomie avec spécialisation data", "Licence pro informatique appliquée"],
  },
  {
    id: "projet-programme",
    label: "Gestion de projets, programmes et partenariats",
    description: "Coordination de projets multi-acteurs, montage, suivi et reporting de programmes techniques ou européens.",
    keywords: ["projet", "programme", "coordinateur", "coordinatrice", "coordination", "chef de projet", "cheffe de projet", "partenariat", "europe", "financement", "reporting", "montage", "pilotage"],
    skills: ["Planification et coordination", "Budget et reporting", "Animation de consortium", "Culture des financements publics"],
    missions: ["Monter et suivre des projets", "Coordonner les livrables et partenaires", "Sécuriser le calendrier et le budget", "Assurer le reporting technique et administratif"],
    activities: ["Réunions de pilotage", "Dossiers de financement", "Suivi d'indicateurs", "Capitalisation des livrables"],
    training: ["Ingénieur ou master agri/agro/environnement", "Master gestion de projet ou politiques publiques", "Expérience de coordination multi-acteurs"],
  },
  {
    id: "terrain-technique",
    label: "Technicien terrain, laboratoire et expérimentation",
    description: "Réalisation opérationnelle des essais, prélèvements, mesures et analyses en appui aux équipes scientifiques.",
    keywords: ["technicien", "technicienne", "terrain", "laboratoire", "labo", "prélèvement", "prelevement", "mesure", "analyses", "assistant technique", "expérimentateur", "experimentateur", "parcelle", "échantillon", "echantillon"],
    skills: ["Rigueur de mesure", "Conduite d'essais", "Matériel agricole ou laboratoire", "Traçabilité des données"],
    missions: ["Mettre en place et suivre les essais", "Réaliser les observations et prélèvements", "Entretenir le matériel et les dispositifs", "Saisir et contrôler les données collectées"],
    activities: ["Notations terrain", "Analyses laboratoire", "Suivi de parcelles ou lots", "Maintenance d'équipements"],
    training: ["BTSA agronomie/productions animales/analyses agricoles", "Licence pro expérimentation ou laboratoire", "Expérience terrain agricole"],
  },
  {
    id: "communication-valorisation",
    label: "Communication, documentation et valorisation",
    description: "Mise en forme des résultats, communication institutionnelle, événementiel et production de contenus.",
    keywords: ["communication", "communicant", "documentation", "documentaliste", "valorisation", "éditorial", "editorial", "contenu", "événement", "evenement", "marketing", "newsletter", "site internet", "réseaux sociaux", "reseaux sociaux"],
    skills: ["Stratégie éditoriale", "Rédaction et vulgarisation", "Communication digitale", "Organisation d'événements"],
    missions: ["Valoriser les travaux techniques", "Produire des contenus web et print", "Organiser des événements", "Animer les canaux de communication"],
    activities: ["Articles et newsletters", "Supports graphiques", "Relations presse", "Gestion documentaire"],
    training: ["Master communication scientifique ou institutionnelle", "École de communication", "Double compétence agri/agro et communication"],
  },
  {
    id: "support-administration",
    label: "Fonctions support, administration et finances",
    description: "Soutien administratif, financier, RH, comptable ou logistique au fonctionnement des instituts et projets.",
    keywords: ["administratif", "administrative", "assistant", "assistante", "gestionnaire", "comptable", "finance", "financier", "rh", "ressources humaines", "juridique", "paie", "secrétaire", "secretaire", "office manager", "achats"],
    skills: ["Gestion administrative", "Suivi budgétaire", "Outils bureautiques et ERP", "Organisation et confidentialité"],
    missions: ["Assurer le suivi administratif et financier", "Préparer les pièces de gestion", "Appuyer les équipes dans la contractualisation", "Suivre les processus RH ou achats"],
    activities: ["Facturation et comptabilité", "Tableaux de suivi", "Gestion de conventions", "Accueil et logistique"],
    training: ["BTS/DUT gestion, comptabilité ou assistant manager", "Licence pro gestion/RH/finance", "Expérience en environnement associatif ou projet"],
  },
  {
    id: "direction-strategie",
    label: "Direction, stratégie et responsabilité d'unité",
    description: "Management d'équipes, orientation stratégique et représentation institutionnelle.",
    keywords: ["directeur", "directrice", "responsable", "manager", "management", "stratégie", "strategie", "direction", "pôle", "pole", "service", "unité", "unite", "lead"],
    skills: ["Management d'équipe", "Vision stratégique", "Pilotage budgétaire", "Représentation institutionnelle"],
    missions: ["Définir une feuille de route", "Manager les équipes et arbitrer les priorités", "Piloter les ressources", "Représenter l'institut auprès des partenaires"],
    activities: ["Comités de direction", "Pilotage RH et budget", "Développement partenarial", "Suivi de performance"],
    training: ["Formation supérieure agri/agro, management ou sciences", "Expérience confirmée de pilotage", "Formation continue en management appréciée"],
  },
];

function normalize(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function matchScore(text: string, keywords: string[]) {
  const normalized = normalize(text);
  return keywords.reduce((score, keyword) => {
    const normalizedKeyword = normalize(keyword);
    return normalized.includes(normalizedKeyword) ? score + (normalizedKeyword.includes(" ") ? 2 : 1) : score;
  }, 0);
}

function summarize(values: Array<string | null | undefined>, max = 6) {
  const counts = new Map<string, number>();
  values.filter(Boolean).forEach((value) => {
    const key = String(value).trim();
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "fr"))
    .slice(0, max)
    .map(([label, count]) => ({ label, count }));
}

export function buildTypology(offers: Offer[]): TypologyProfile[] {
  const buckets = PROFILE_DEFINITIONS.map((definition) => ({ definition, offers: [] as Offer[] }));
  const fallback = {
    definition: {
      id: "autres-profils",
      label: "Autres profils ou intitulés transverses",
      description: "Offres ne présentant pas assez de signaux textuels pour être rattachées automatiquement à une famille dominante.",
      keywords: [],
      skills: ["Polyvalence", "Adaptation au contexte ITA", "Travail en équipe", "Culture agricole ou agroalimentaire"],
      missions: ["Contribuer aux activités de l'institut", "Appuyer les équipes métiers", "Participer au suivi des projets", "Documenter les résultats"],
      activities: ["Appui opérationnel", "Coordination interne", "Suivi documentaire", "Relations partenaires"],
      training: ["Formation adaptée au domaine de l'offre", "Expérience dans les filières agricoles appréciée"],
    },
    offers: [] as Offer[],
  };

  offers.forEach((offer) => {
    const haystack = [offer.title, offer.offer_type, offer.contract_type, offer.organization, offer.source_name, offer.location_text, offer.description_text].filter(Boolean).join(" ");
    const ranked = buckets
      .map((bucket) => ({ bucket, score: matchScore(haystack, bucket.definition.keywords) }))
      .sort((a, b) => b.score - a.score);

    if (ranked[0]?.score > 0) {
      ranked[0].bucket.offers.push(offer);
    } else {
      fallback.offers.push(offer);
    }
  });

  return [...buckets, fallback]
    .filter((bucket) => bucket.offers.length > 0)
    .sort((a, b) => b.offers.length - a.offers.length || a.definition.label.localeCompare(b.definition.label, "fr"))
    .map(({ definition, offers: profileOffers }) => ({
      id: definition.id,
      label: definition.label,
      description: definition.description,
      count: profileOffers.length,
      activeCount: profileOffers.filter((offer) => !offer.archived_at).length,
      archivedCount: profileOffers.filter((offer) => Boolean(offer.archived_at)).length,
      skills: definition.skills,
      missions: definition.missions,
      activities: definition.activities,
      training: definition.training,
      sources: summarize(profileOffers.map((offer) => offer.source_name)),
      contractTypes: summarize(profileOffers.map((offer) => offer.contract_type), 4),
      offerTypes: summarize(profileOffers.map((offer) => offer.offer_type), 4),
      examples: profileOffers
        .slice()
        .sort((a, b) => (b.last_seen_at ?? "").localeCompare(a.last_seen_at ?? ""))
        .slice(0, 5)
        .map((offer) => ({ id: offer.id, title: offer.title, sourceName: offer.source_name, archived: Boolean(offer.archived_at) })),
    }));
}
