import random

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from perfumery.models import Category, Product


# Descriptions use familiar fragrance profiles while avoiding unsupported claims
# about an individual bottle's performance.
PRODUCTS = [
    ('Asad', 'Lattafa', 'Men', 'A bold blend of black pepper, warm spice, and creamy vanilla. Its dark amber character suits evenings and cooler weather.'),
    ('Khamrah', 'Lattafa', 'Unisex', 'Cinnamon, dates, and praline create a rich gourmand opening. Vanilla and amberwood leave a warm, inviting trail.'),
    ('Yara', 'Lattafa', 'Women', 'Soft tropical fruit and delicate florals meet a creamy vanilla accord. The sweet, playful profile works beautifully for everyday wear.'),
    ('Fakhar Black', 'Lattafa', 'Men', 'Fresh citrus and aromatic herbs open this polished, modern scent. Woods and amber give it a smooth finish for day or evening.'),
    ('Qaed Al Fursan', 'Lattafa', 'Unisex', 'Juicy pineapple and saffron bring a bright opening with a subtle smoky edge. Woody notes round out this distinctive casual fragrance.'),
    ("Bade'e Al Oud Oud for Glory", 'Lattafa', 'Unisex', 'Saffron and nutmeg introduce a bold oud and patchouli heart. Rich woods and musk make this a confident choice for evening occasions.'),
    ('Nebras', 'Lattafa', 'Unisex', 'Red berries and cocoa create a smooth, sweet first impression. Vanilla and amber add a cozy finish suited to relaxed evenings.'),
    ('Mayar', 'Lattafa', 'Women', 'Litchi and raspberry bring a bright fruity start to this feminine fragrance. White florals and vanilla keep the dry-down soft and elegant.'),
    ('Hayaati', 'Lattafa', 'Men', 'Crisp apple and cinnamon give this scent an energetic, spicy opening. Woods and musk provide an easygoing finish for daily use.'),
    ('Ana Abiyedh Rouge', 'Lattafa', 'Unisex', 'Saffron and bitter almond give this fragrance a distinctive, airy sweetness. Amber and woods add a smooth finish that transitions easily from day to night.'),
    ('Club de Nuit Intense Man', 'Armaf', 'Men', 'Bright lemon and pineapple lead into a confident smoky-wood accord. A polished choice for evenings, celebrations, and signature wear.'),
    ('Club de Nuit Woman', 'Armaf', 'Women', 'Citrus and peach open with a fresh, lively character. Rose, jasmine, and soft woods make the finish graceful and versatile.'),
    ('Club de Nuit Untold', 'Armaf', 'Unisex', 'Saffron and jasmine create a luminous opening with a refined floral feel. Amberwood adds depth for a memorable evening scent.'),
    ('Club de Nuit Milestone', 'Armaf', 'Unisex', 'Sea notes and red fruit bring a breezy, sunlit character. Musk and woods keep the finish smooth for warm-weather wear.'),
    ('Club de Nuit Sillage', 'Armaf', 'Unisex', 'Citrus and blackcurrant give this fragrance a crisp, sparkling start. Iris and musk add a clean, elegant character for daytime.'),
    ('Tres Nuit', 'Armaf', 'Men', 'Green notes and lemon make a fresh, confident first impression. Violet and woods keep the character refined and easy to wear.'),
    ('Odyssey Mandarin Sky', 'Armaf', 'Men', 'Mandarin and orange blossom bring a bright, energetic opening. Tonka and amber add a warm gourmand finish for evenings out.'),
    ('Odyssey Homme', 'Armaf', 'Men', 'Cardamom and citrus create a crisp, aromatic introduction. Vanilla, amber, and woods settle into a smooth, versatile finish.'),
    ('Hunter Intense', 'Armaf', 'Men', 'Bergamot and lemon lend this scent a fresh, sporty start. Spices and woods add a confident finish for everyday occasions.'),
    ('9PM', 'Afnan', 'Men', 'Apple and cinnamon bring a lively, sweet-spiced opening. Vanilla and amber give this evening fragrance a warm, inviting character.'),
    ('Supremacy Not Only Intense', 'Afnan', 'Men', 'Blackcurrant and bergamot create a vibrant fruity opening. Oakmoss and amber add depth to this bold, polished composition.'),
    ('Turathi Blue', 'Afnan', 'Men', 'Grapefruit and citrus deliver a crisp, refreshing introduction. Amber and woods create a clean finish that suits daytime wear.'),
    ('Modest Une', 'Afnan', 'Men', 'Fresh citrus and aromatic spices open with an energetic edge. Leather and woods give the fragrance a smooth, confident finish.'),
    ('Rare Tiffany', 'Afnan', 'Women', 'Fruity notes and citrus bring a bright, feminine opening. White florals and musk create a soft, polished finish for day or evening.'),
    ('Supremacy Silver', 'Afnan', 'Men', 'Pineapple and bergamot give this fragrance a crisp, fruit-forward start. Birch and musk add a clean woody character for versatile wear.'),
    ('Historic Olmeda', 'Afnan', 'Unisex', 'Citrus and aromatic notes open with a fresh, composed feel. Woods and amber provide a refined finish for daily wear.'),
    ('Toscano Leather', 'Maison Alhambra', 'Unisex', 'Raspberry and saffron soften a rich leather accord. Amber and woods create a bold, dressed-up scent for cooler evenings.'),
    ('Porto Neroli', 'Maison Alhambra', 'Unisex', 'Neroli and orange blossom bring a bright, breezy Mediterranean feel. White musk keeps the finish clean and relaxed for warm days.'),
    ('Lovely Cherie', 'Maison Alhambra', 'Women', 'Black cherry and almond create a luscious, sweet opening. Rose and tonka add a smooth finish with a touch of elegance.'),
    ('Bright Peach', 'Maison Alhambra', 'Unisex', 'Juicy peach and blood orange make this fragrance cheerful and fruit-forward. Honey and vanilla bring a soft, rounded finish.'),
    ('Kismet Angel', 'Maison Alhambra', 'Unisex', 'Honey and cognac notes create a rich, welcoming opening. Cinnamon and vanilla make the finish feel warm and indulgent.'),
    ('Yeah!', 'Maison Alhambra', 'Men', 'Apple and ginger give this fragrance a fresh, energetic start. Sage and woods create a clean, modern profile for everyday wear.'),
    ('Jean Lowe Immortal', 'Maison Alhambra', 'Men', 'Grapefruit and ginger bring a crisp citrus opening. Amber and incense add a smooth, quietly distinctive finish.'),
    ('Barakkat Rouge 540', 'Fragrance World', 'Unisex', 'Saffron and jasmine form a bright, airy opening. Amberwood and cedar create a warm, refined finish for special occasions.'),
    ('Imperium', 'Fragrance World', 'Men', 'Bergamot and pineapple open with a fresh, confident character. Patchouli and amber add a smooth finish for evening wear.'),
    ('Proud of You', 'Fragrance World', 'Men', 'Lavender and cinnamon bring an aromatic, gently sweet opening. Vanilla and amber create a cozy, polished finish.'),
    ('Intro Aftermath', 'Fragrance World', 'Men', 'Fresh citrus meets aromatic herbs for a lively introduction. Woods and musk bring a composed finish suited to daily wear.'),
    ('Mocha Wood', 'Fragrance World', 'Unisex', 'Coffee and spice create a rich opening with a roasted warmth. Vanilla and woods soften the finish into a smooth gourmand scent.'),
    ('Cocktail Intense', 'Fragrance World', 'Unisex', 'Warm spices and boozy accords open with an inviting richness. Vanilla and woods make the dry-down smooth and evening-ready.'),
    ('Harmony Code Absolute', 'Fragrance World', 'Men', 'Citrus and aromatic herbs start with a clean, refined feel. Tonka and woods add a warm finish for smart occasions.'),
    ('Hawas', 'Rasasi', 'Men', 'Crisp apple and citrus bring a refreshing, aquatic opening. Amber and musk create a lively finish for warm days and nights.'),
    ('La Yuqawam Pour Homme', 'Rasasi', 'Men', 'Saffron and raspberry meet a rich leather heart. Amber and woods give this elegant scent a distinctive evening character.'),
    ('Daarej', 'Rasasi', 'Men', 'Cardamom and cumin create a warm, spicy introduction. Rose and vanilla smooth the finish into a refined, comfortable fragrance.'),
    ('Shuhrah Pour Homme', 'Rasasi', 'Men', 'Tomato leaf and smoky notes make a striking green opening. Leather and woods create a bold profile for those who enjoy distinctive scents.'),
    ('Fattan', 'Rasasi', 'Men', 'Grapefruit and green notes bring a bright, earthy freshness. Vetiver and patchouli give the finish a composed, versatile character.'),
    ('Wisal Dhahab', 'Ajmal', 'Women', 'Apple and pear open with a bright, fruity sweetness. Rose and musk create a graceful finish for everyday elegance.'),
    ('Aristocrat for Her', 'Ajmal', 'Women', 'Citrus and fruity notes introduce a radiant feminine scent. Rose, patchouli, and amber give it a poised, lasting character.'),
    ('Evoke Gold Edition', 'Ajmal', 'Men', 'Fresh citrus and aromatic spices open with a polished feel. Leather and woods add a smooth finish for work or evening wear.'),
    ('Kuro', 'Ajmal', 'Men', 'Bergamot and pepper make a crisp, energetic first impression. Vetiver and woods settle into a clean, confident everyday scent.'),
    ('Amber Wood', 'Ajmal', 'Unisex', 'Citrus and cardamom brighten a rich amber opening. Patchouli and woods create a luxurious, balanced finish for special occasions.'),
]


class Command(BaseCommand):
    help = 'Seed the catalog with 50 realistic designer and Arabian fragrances.'

    def handle(self, *args, **options):
        if len(PRODUCTS) != 50:
            raise CommandError(f'Expected 50 catalog entries, found {len(PRODUCTS)}.')

        categories = {
            name: Category.objects.get_or_create(name=name)[0]
            for name in ('Men', 'Women', 'Unisex')
        }
        rng = random.Random(20260927)
        created = 0

        for name, brand, category_name, description in PRODUCTS:
            base_slug = slugify(name)
            slug = base_slug
            suffix = 2
            while Product.objects.filter(slug=slug).exclude(name=name).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1

            _product, was_created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'brand': brand,
                    'category': categories[category_name],
                    'price': rng.randrange(36, 191) * 500,
                    'stock': rng.randint(0, 40),
                    'volume_ml': rng.choice((30, 50, 60, 90, 100, 105)),
                    'description': description,
                    'is_active': True,
                },
            )
            created += int(was_created)

        self.stdout.write(self.style.SUCCESS(
            f'Catalog seed complete: {created} products created from {len(PRODUCTS)} entries.'
        ))
